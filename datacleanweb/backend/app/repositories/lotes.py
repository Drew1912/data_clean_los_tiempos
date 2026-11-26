from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from flask import current_app, g
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from ..services.errors import InputError
from ..services.auditing import record


@contextmanager
def connection():
    with psycopg.connect(current_app.config["DATABASE_URL"], connect_timeout=3, row_factory=dict_row) as conn:
        yield conn


def checked_id(value):
    try:
        return UUID(str(value))
    except ValueError as error:
        raise InputError("ID_INVALIDO", "El identificador de lote no es válido") from error


def get_lot(lot_id, conn):
    lot = conn.execute("SELECT *, vence_en <= CURRENT_TIMESTAMP AS vencido FROM lote WHERE id=%s", (checked_id(lot_id),)).fetchone()
    if not lot:
        raise InputError("LOTE_NO_ENCONTRADO", "El lote no existe", 404)
    if lot["vencido"] or lot["estado"] == "vencido":
        raise InputError("LOTE_VENCIDO", "El lote venció; realiza una nueva carga", 410)
    return lot


def add_observation(conn, issue):
    fields = ("archivo_id", "registro_id", "hoja", "fila", "linea_fin", "campo", "valor_original", "tipo", "motivo", "grupo_candidato", "regla")
    conn.execute(
        "INSERT INTO observacion(archivo_id,registro_id,hoja,fila,linea_fin,campo,valor_original,tipo,motivo,grupo_candidato,regla) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", [issue.get(key) for key in fields])


def create_lot(lot_id, files, issues):
    with connection() as conn:
        conn.execute("INSERT INTO lote(id,vence_en,creado_por) VALUES (%s,CURRENT_TIMESTAMP + INTERVAL '24 hours',%s)",
                     (lot_id, (getattr(g, "usuario", None) or {}).get("id")))
        for f in files:
            conn.execute(
                "INSERT INTO archivo(id,lote_id,posicion,nombre_original,nombre_interno,extension,bytes,sha256,perfil_id,perfil_version,perfil_snapshot,estado,hojas) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (f["id"], lot_id, f["posicion"], f["nombre_original"], f["nombre_interno"], f["extension"], f["bytes"], f["sha256"],
                 f.get("perfil_id"), f.get("perfil_version"), Jsonb(f["perfil_snapshot"]) if f["perfil_snapshot"] else None,
                 f["estado"], Jsonb(f["hojas"])))
        for issue in issues:
            add_observation(conn, issue)
        record(conn, "LOTE_CARGADO", lot_id=lot_id, details={"archivos":len(files), "admitidos":sum(f["estado"]=="admitido" for f in files), "rechazados":sum(f["estado"]=="rechazado" for f in files)})


def files_for_lot(lot_id, conn):
    return conn.execute("SELECT * FROM archivo WHERE lote_id=%s ORDER BY posicion", (lot_id,)).fetchall()


def describe(lot_id):
    with connection() as conn:
        lot = get_lot(lot_id, conn)
        files = files_for_lot(lot["id"], conn)
        for f in files:
            reasons = conn.execute("SELECT motivo FROM observacion WHERE archivo_id=%s AND registro_id IS NULL ORDER BY id", (f["id"],)).fetchall()
            f["motivos"] = [r["motivo"] for r in reasons]
        return {"lote_id": str(lot["id"]), "estado": lot["estado"], "vence_en": lot["vence_en"].isoformat(),
                "archivos": [{"id": str(f["id"]), "indice": f["posicion"], "nombre": f["nombre_original"], "estado": f["estado"],
                              "hojas": f["hojas"], "motivos": f["motivos"], "perfil_id": f["perfil_id"],
                              "perfil_descripcion": (f["perfil_snapshot"] or {}).get("descripcion"),
                              "nivel": (f["perfil_snapshot"] or {}).get("nivel"),
                              "columna_contrato": (f["perfil_snapshot"] or {}).get("columna_contrato")} for f in files],
                "advertencias": warnings(files), "puede_procesar": lot["estado"] == "cargado" and any(f["estado"] == "admitido" for f in files)}


def warnings(files):
    return list(dict.fromkeys(note for f in files if f["perfil_snapshot"]
                             for note in f["perfil_snapshot"].get("advertencias", [])))


def claim_processing(lot_id, classification=None):
    with connection() as conn:
        conn.execute("SELECT id FROM lote WHERE id=%s FOR UPDATE", (checked_id(lot_id),))
        lot = get_lot(lot_id, conn)
        files = files_for_lot(lot["id"], conn)
        configured = {}
        if classification is not None:
            if not isinstance(classification, dict) or set(classification) != {"contratos"} or not isinstance(classification["contratos"], list):
                raise InputError("CLASIFICACION_INVALIDA", "Envía la columna de contrato de cada archivo admitido")
            admitted = {str(f["id"]):f for f in files if f["estado"] == "admitido"}
            for item in classification["contratos"]:
                if not isinstance(item, dict) or set(item) != {"archivo_id", "columna"} or not isinstance(item["archivo_id"], str):
                    raise InputError("CLASIFICACION_INVALIDA", "Cada selección requiere archivo_id y columna")
                fid, column = item["archivo_id"], item["columna"]
                if fid not in admitted or fid in configured:
                    raise InputError("ARCHIVO_INVALIDO", "Selecciona una sola vez cada archivo admitido de este lote")
                known = {name for sheet in admitted[fid]["hojas"] if sheet.get("estado") == "admitida" for name in sheet.get("columnas", [])}
                if column is not None and (not isinstance(column, str) or column not in known):
                    raise InputError("COLUMNA_DESCONOCIDA", "La columna de contrato no pertenece al archivo")
                configured[fid] = column
            if set(configured) != set(admitted):
                raise InputError("CLASIFICACION_INVALIDA", "Configura todos los archivos admitidos; usa null cuando no haya contrato")
        if lot["estado"] == "completado":
            if classification is not None and any(f["perfil_snapshot"].get("departamento_activo") is not False or f["perfil_snapshot"].get("columna_contrato") != configured[str(f["id"])] for f in files if f["estado"] == "admitido"):
                raise InputError("CLASIFICACION_INMUTABLE", "El lote ya se procesó con otra clasificación; crea una carga nueva para cambiar columnas", 409)
            return None
        if lot["estado"] != "cargado":
            raise InputError("ESTADO_INCOMPATIBLE", "El lote ya se está procesando o falló; revisa su estado", 409)
        if not any(f["estado"] == "admitido" for f in files):
            raise InputError("SIN_ARCHIVOS_ADMITIDOS", "El lote no contiene cabeceras admitidas", 409)
        changed = conn.execute("UPDATE lote SET estado='procesando', iniciado_en=CURRENT_TIMESTAMP WHERE id=%s AND estado='cargado' RETURNING id", (lot["id"],)).fetchone()
        if not changed:
            raise InputError("PROCESANDO", "Otra petición comenzó el procesamiento de este lote", 409)
        if classification is not None:
            for file in files:
                if file["estado"] != "admitido":
                    continue
                profile = file["perfil_snapshot"]
                profile["departamento_activo"] = False
                profile["columna_contrato"] = configured[str(file["id"])]
                profile["obligatorios"] = [key for key in profile["obligatorios"] if key != "caja_codigo" and not (key == "modalidad_codigo" and profile["columna_contrato"])]
                conn.execute("UPDATE archivo SET perfil_snapshot=%s WHERE id=%s", (Jsonb(profile), file["id"]))
            record(conn, "CLASIFICACION_CONFIGURADA", lot_id=lot["id"], details={"archivos":len(configured), "contratos":sum(value is not None for value in configured.values())})
        return files


def complete(lot_id, rows, issues):
    fields = ("id", "archivo_id", "hoja", "fila", "linea_fin", "original", "adicionales", "cambios", "numero_factura", "fecha_factura",
              "nit_ci", "modalidad_codigo", "caja_codigo", "monto_numeral", "razon_social", "cuf", "anulado", "modalidad", "departamento", "estado")
    statement = "INSERT INTO registro(" + ",".join(fields) + ") VALUES (" + ",".join(["%s"] * len(fields)) + ")"
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(statement, [[Jsonb(row[key]) if key in {"original", "adicionales", "cambios"} else row[key] for key in fields] for row in rows])
        for issue in issues:
            add_observation(conn, issue)
        conn.execute("UPDATE lote SET estado='completado', finalizado_en=CURRENT_TIMESTAMP WHERE id=%s AND estado='procesando'", (checked_id(lot_id),))
        record(conn, "LOTE_PROCESADO", lot_id=checked_id(lot_id), details={"registros":len(rows), "validos":sum(r["estado"]=="valido" for r in rows), "observados":sum(r["estado"]=="observado" for r in rows), "cambios":sum(len(r["cambios"]) for r in rows), "observaciones":len(issues)})


def mark_failed(lot_id):
    with connection() as conn:
        conn.execute("UPDATE lote SET estado='fallido', finalizado_en=CURRENT_TIMESTAMP WHERE id=%s AND estado='procesando'", (checked_id(lot_id),))


def selection(modality="todos", department="todos"):
    if modality not in {"todos", "contado", "credito"} or department not in {"todos", "cochabamba", "la_paz", "santa_cruz"}:
        raise InputError("FILTRO_INVALIDO", "Modalidad o departamento no admitidos")
    return modality, department


def _where(lot_id, modality, department, state="valido"):
    modality, department = selection(modality, department)
    if state not in {"todos", "valido", "observado"}:
        raise InputError("ESTADO_INVALIDO", "El estado debe ser todos, valido u observado")
    return ("a.lote_id=%s AND (%s='todos' OR r.estado=%s) AND (%s='todos' OR r.modalidad=%s) "
            "AND (%s='todos' OR r.departamento=%s)", (lot_id, state, state, modality, modality, department, department))


def summary(lot_id, modality="todos", department="todos"):
    modality, department = selection(modality, department)
    with connection() as conn:
        lot = get_lot(lot_id, conn)
        files = files_for_lot(lot["id"], conn)
        counters = dict.fromkeys(("cargados", "validos", "observados", "seleccionados", "exportados"))
        if lot["estado"] == "completado":
            counters.update(conn.execute(
                "SELECT COUNT(*) AS cargados, COUNT(*) FILTER(WHERE r.estado='valido') AS validos, "
                "COUNT(*) FILTER(WHERE r.estado='observado') AS observados FROM registro r JOIN archivo a ON a.id=r.archivo_id WHERE a.lote_id=%s", (lot["id"],)).fetchone())
            where, params = _where(lot["id"], modality, department)
            counters["seleccionados"] = conn.execute("SELECT COUNT(*) AS n FROM registro r JOIN archivo a ON a.id=r.archivo_id WHERE " + where, params).fetchone()["n"]
            counters["exportados"] = (lot["ultima_exportacion"] or {}).get("cantidad", 0)
        issue_counts = conn.execute(
            "SELECT COUNT(*) FILTER(WHERE o.registro_id IS NOT NULL) AS fila, COUNT(*) FILTER(WHERE o.registro_id IS NULL) AS estructura "
            "FROM observacion o JOIN archivo a ON a.id=o.archivo_id WHERE a.lote_id=%s", (lot["id"],)).fetchone()
        return {"lote_id": str(lot["id"]), "estado": lot["estado"], "registros": counters,
                "archivos": {"recibidos": len(files), "admitidos": sum(f["estado"] == "admitido" for f in files), "rechazados": sum(f["estado"] == "rechazado" for f in files)},
                "cantidad_observaciones_fila": issue_counts["fila"], "cantidad_observaciones_estructura": issue_counts["estructura"],
                "filtros": {"modalidad": modality, "departamento": department}, "ultima_exportacion": lot["ultima_exportacion"], "advertencias": warnings(files)}


def scalar(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    return value


def normalized_record(row):
    return dict({key: scalar(row.get(key)) for key in ("numero_factura", "fecha_factura", "nit_ci", "monto_numeral",
             "razon_social", "modalidad_codigo", "caja_codigo", "modalidad", "departamento", "cuf", "anulado", "estado")},
             nivel_registro=row.get("nivel_registro") or "cabecera")


def valid_records(lot_id, page, size, modality="todos", department="todos", state="valido"):
    with connection() as conn:
        lot = get_lot(lot_id, conn)
        if lot["estado"] != "completado":
            raise InputError("LOTE_NO_COMPLETADO", "Primero procesa el lote", 409)
        where, params = _where(lot["id"], modality, department, state)
        total = conn.execute("SELECT COUNT(*) AS n FROM registro r JOIN archivo a ON a.id=r.archivo_id WHERE " + where, params).fetchone()["n"]
        rows = conn.execute("SELECT r.*, a.nombre_original,a.perfil_snapshot->>'nivel' AS nivel_registro FROM registro r JOIN archivo a ON a.id=r.archivo_id WHERE " + where +
                            " ORDER BY a.posicion,r.hoja NULLS FIRST,r.fila,r.id LIMIT %s OFFSET %s", (*params, size, (page - 1) * size)).fetchall()
        data = []
        for row in rows:
            notes = conn.execute("SELECT tipo,motivo,grupo_candidato FROM observacion WHERE registro_id=%s ORDER BY id", (row["id"],)).fetchall()
            data.append(dict(normalized_record(row), id=str(row["id"]), adicionales=row["adicionales"], cambios=row["cambios"],
                             origen=origin(row), advertencias=notes))
        return {"datos": data, "pagina": page, "tamano": size, "total": total}


def origin(row):
    return {"archivo_id": str(row["archivo_id"]), "archivo": row["nombre_original"],
            "hoja": row["hoja"], "fila": row["fila"], "linea_fin": row["linea_fin"]}


def observations(lot_id, page, size):
    with connection() as conn:
        lot = get_lot(lot_id, conn)
        total = conn.execute("SELECT COUNT(*) AS n FROM observacion o JOIN archivo a ON a.id=o.archivo_id WHERE a.lote_id=%s", (lot["id"],)).fetchone()["n"]
        rows = conn.execute(
            "SELECT o.*,a.nombre_original,r.original AS registro_original,r.numero_factura,r.fecha_factura,r.nit_ci,r.monto_numeral,"
            "r.razon_social,r.modalidad_codigo,r.caja_codigo,r.modalidad,r.departamento,r.cuf,r.anulado,r.estado "
            "FROM observacion o JOIN archivo a ON a.id=o.archivo_id LEFT JOIN registro r ON r.id=o.registro_id "
            "WHERE a.lote_id=%s ORDER BY a.posicion,o.hoja NULLS FIRST,o.fila NULLS FIRST,o.id LIMIT %s OFFSET %s",
            (lot["id"], size, (page - 1) * size)).fetchall()
        data = []
        for row in rows:
            item = {key: scalar(row[key]) for key in ("id", "registro_id", "tipo", "campo", "motivo", "valor_original", "grupo_candidato", "regla")}
            item.update(origen=origin(row), registro_original=row["registro_original"],
                        registro_normalizado=normalized_record(row) if row["registro_id"] else None)
            data.append(item)
        return {"datos": data, "pagina": page, "tamano": size, "total": total}


def relation_records(lot_id):
    with connection() as conn:
        lot = get_lot(lot_id, conn)
        if lot["estado"] != "completado":
            raise InputError("LOTE_NO_COMPLETADO", "Primero procesa el lote", 409)
        rows = conn.execute("SELECT r.*,a.nombre_original,a.perfil_snapshot->>'nivel' AS nivel_registro FROM registro r "
                            "JOIN archivo a ON a.id=r.archivo_id WHERE a.lote_id=%s ORDER BY a.posicion,r.fila", (lot["id"],)).fetchall()
        return [dict(normalized_record(r), id=str(r["id"]), origen=origin(r)) for r in rows]


def comparison_context(lot_id):
    with connection() as conn:
        lot = get_lot(lot_id, conn)
        if lot["estado"] != "completado":
            raise InputError("LOTE_NO_COMPLETADO", "Primero procesa el lote", 409)
        files = files_for_lot(lot["id"], conn)
        rows = conn.execute("SELECT r.* FROM registro r JOIN archivo a ON a.id=r.archivo_id "
                            "WHERE a.lote_id=%s ORDER BY a.posicion,r.hoja,r.fila,r.id", (lot["id"],)).fetchall()
        return files, rows


def export_snapshot(lot_id, modality, department, clean, conn):
    # Serializa exportaciones y purga del mismo lote; no modifica los registros.
    conn.execute("SELECT id FROM lote WHERE id=%s FOR UPDATE", (checked_id(lot_id),)).fetchone()
    lot = get_lot(lot_id, conn)
    if (clean and lot["estado"] != "completado") or lot["estado"] == "procesando":
        raise InputError("ESTADO_INCOMPATIBLE", "Espera a que el lote termine de procesarse antes de exportar", 409)
    files = files_for_lot(lot["id"], conn)
    where, params = _where(lot["id"], modality, department, "valido" if clean else "todos")
    rows = conn.execute("SELECT r.*,a.nombre_original FROM registro r JOIN archivo a ON a.id=r.archivo_id WHERE " + where +
                        " ORDER BY a.posicion,r.hoja NULLS FIRST,r.fila,r.id", params).fetchall()
    issues = conn.execute("SELECT o.*,a.nombre_original FROM observacion o JOIN archivo a ON a.id=o.archivo_id "
                          "WHERE a.lote_id=%s ORDER BY a.posicion,o.hoja NULLS FIRST,o.fila NULLS FIRST,o.id", (lot["id"],)).fetchall()
    return lot, files, rows, issues


def save_export(lot_id, metadata, conn):
    conn.execute("UPDATE lote SET ultima_exportacion=%s WHERE id=%s", (Jsonb(metadata), lot_id))
