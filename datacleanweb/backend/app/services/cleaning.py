"""Etapas adaptadas de clean_data del prototipo: sin dropna, float ni round.

Las reglas empresariales pendientes no se infieren. Los formatos y el pequeño
catálogo de demostración pertenecen al perfil versionado, no a una regla universal.
"""
from datetime import datetime, date, time
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from uuid import uuid4


def clean_text(value):
    # Reutilización de strip del algoritmo base, con espacios internos para texto.
    return " ".join(value.split())


def identifier(source, allow_scientific_text=False):
    value = source["valor"].strip()
    if any(ord(character) < 32 for character in value):
        raise ValueError("El identificador contiene caracteres de control")
    if source["tipo"] == "numero":
        if not re.fullmatch(r"[0-9]+", value) or len(value.lstrip("0")) > 15:
            raise ValueError("Identificador numérico ambiguo o con posible pérdida de precisión")
        fmt = source.get("formato", "")
        if re.fullmatch(r"0{1,50}", fmt):
            value = value.zfill(len(fmt))
    elif not allow_scientific_text and re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?[eE][+-]?[0-9]+", value):
        raise ValueError("El identificador está en notación científica; debe revisarse como texto")
    return value


def exact_amount(source, profile):
    value = source["valor"].strip()
    if len(value) > 100:
        raise ValueError("Importe demasiado largo")
    if source["tipo"] == "numero":
        canonical = value  # XML numérico original; nunca str(float) ni inferencia Pandas.
    elif "decimal_punto" in profile["formatos_numero"] and re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]{1,2})?", value):
        canonical = value
    elif "decimal_coma" in profile["formatos_numero"] and re.fullmatch(r"[+-]?[0-9]+,[0-9]{1,2}", value):
        canonical = value.replace(",", ".")
    elif "miles_punto_decimal_coma" in profile["formatos_numero"] and re.fullmatch(r"[+-]?[0-9]{1,3}(?:\.[0-9]{3})+,[0-9]{1,2}", value):
        canonical = value.replace(".", "").replace(",", ".")
    else:
        raise ValueError("Formato monetario ambiguo o no admitido por el perfil")
    try:
        amount = Decimal(canonical)
        if not amount.is_finite() or abs(amount.as_tuple().exponent) > 100:
            raise ValueError("Importe no finito o fuera de la representación admitida")
        if amount < Decimal(profile["importe_minimo"]):
            raise ValueError("Importe menor al mínimo declarado por el perfil")
        if amount.as_tuple().exponent < -profile["escala_maxima"]:
            raise ValueError("El importe tiene más decimales de los permitidos; no se redondeó")
        return amount
    except InvalidOperation as error:
        raise ValueError("El importe no es un decimal válido") from error


def invoice_date(source, profile):
    if source["tipo"] == "fecha_excel":
        value = datetime.fromisoformat(source["fecha_iso"])
        if value.time() != time(0):
            raise ValueError("La fecha contiene hora; el perfil no autoriza descartarla")
        return value.date()
    value = source["valor"].strip()
    candidates = set()
    for fmt in profile["formatos_fecha"]:
        try:
            candidates.add(datetime.strptime(value, fmt).date())
        except ValueError:
            pass
    if len(candidates) != 1:
        raise ValueError("Fecha imposible, ambigua o incompatible con el perfil")
    return candidates.pop()


def observation(row, field, kind, reason, original=None):
    return {"registro_id": row["id"], "archivo_id": row["archivo_id"],
            "hoja": row["hoja"], "fila": row["fila"], "linea_fin": row["linea_fin"],
            "campo": field, "tipo": kind, "motivo": reason, "valor_original": original,
            "regla": "limpieza_perfil_v1", "grupo_candidato": None}


def clean_record(source, file_id, profile):
    fields = [*profile["alias"], "modalidad", "departamento"]
    row = dict.fromkeys(fields)
    row.update(id=uuid4(), archivo_id=file_id, hoja=source["hoja"], fila=source["fila"],
               linea_fin=source["linea_fin"], original=source["original"], cambios=[],
               nivel_registro=profile.get("nivel", "cabecera"),
               adicionales={k: v for k, v in source["original"].items() if k not in source["mapeo"].values()})
    issues = []
    if all(not c["valor"].strip() for c in source["original"].values()):
        issues.append(observation(row, None, "FILA_VACIA", "Fila completamente vacía dentro del bloque de datos"))
    else:
        for field in profile["alias"]:
            raw = source["original"].get(source["mapeo"].get(field))
            if field == "modalidad_codigo" and profile.get("columna_contrato"):
                continue
            if field == "caja_codigo" and profile.get("departamento_activo") is False:
                row[field] = raw["valor"] if raw and raw["valor"].strip() else None
                continue
            if raw is None or not raw["valor"].strip():
                if field in profile["obligatorios"]:
                    issues.append(observation(row, field, "CAMPO_OBLIGATORIO", "Falta un campo obligatorio", raw["valor"] if raw else None))
                continue
            try:
                if field == "anulado":
                    row[field] = raw["valor"]  # Puede ser un booleano/código; no interpretarlo como regla de exclusión.
                    continue
                if raw["tipo"] in {"formula", "booleano", "error_excel"} or (raw["tipo"] == "fecha_excel" and field != "fecha_factura"):
                    if field not in profile["obligatorios"]:
                        row[field] = raw["valor"]
                        issues.append(observation(row, field, "AVISO_VALOR_NO_INTERPRETADO", "Valor complementario conservado sin evaluar ni interpretar", raw["valor"]))
                        continue
                    raise ValueError("Tipo de celda incompatible con el campo; no se evaluó ni reinterpretó")
                if field == "monto_numeral":
                    value = exact_amount(raw, profile)
                elif field == "fecha_factura":
                    value = invoice_date(raw, profile)
                elif field in {"numero_factura", "nit_ci", "cuf", "caja_codigo"}:
                    value = identifier(raw, allow_scientific_text=field == "cuf")
                    if field == "caja_codigo":
                        value = value.upper()
                elif field == "modalidad_codigo":
                    value = raw["valor"].strip().upper()
                elif field == "razon_social":
                    value = clean_text(raw["valor"])
                else:
                    value = raw["valor"]  # ANULADO se conserva sin interpretación.
                row[field] = value
                canonical = value.isoformat() if isinstance(value, date) else str(value)
                if canonical != raw["valor"]:
                    row["cambios"].append({"campo": field, "original": raw["valor"], "normalizado": canonical,
                                           "regla": "normalizacion_segura_v1"})
            except ValueError as error:
                kind = {"monto_numeral": "MONTO_INVALIDO", "fecha_factura": "FECHA_INVALIDA"}.get(field, "VALOR_INVALIDO")
                issues.append(observation(row, field, kind, str(error), raw["valor"]))
        # Clasificación mínima estricta necesaria para el estado válido del esquema.
        # El catálogo solo pertenece al perfil DEMO; no habilita códigos empresariales.
        if profile.get("columna_contrato"):
            column = profile["columna_contrato"]
            contract = source["original"].get(column)
            try:
                if not contract or not contract["valor"].strip():
                    raise ValueError("Contrato vacío o columna ausente en esta hoja; no se infirió modalidad")
                if contract["tipo"] not in {"texto", "numero"}:
                    raise ValueError("Contrato no comparable: no se evalúan fórmulas ni fechas")
                prefix = identifier(contract)[:1].upper()
                if prefix not in {"C", "P"}:
                    raise ValueError("El contrato debe comenzar por C (Contado) o P (Crédito)")
                row["modalidad_codigo"] = prefix
                row["cambios"].append({"campo": "modalidad_codigo", "original": contract["valor"], "normalizado": prefix,
                                       "regla": "prefijo_contrato_v1:" + column})
                native = source["original"].get(source["mapeo"].get("modalidad_codigo"))
                if native and native["valor"].strip().upper() in {"C", "P"} and native["valor"].strip().upper() != prefix:
                    issues.append(observation(row, "modalidad_codigo", "AVISO_MODALIDAD_CONFLICTIVA", "La columna C/P difiere del contrato elegido; se utilizó el prefijo del contrato y se conservaron ambos originales", native["valor"]))
            except ValueError as error:
                issues.append(observation(row, column, "CONTRATO_INVALIDO", str(error), contract["valor"] if contract else None))
        code = row["modalidad_codigo"]
        row["modalidad"] = {"C": "contado", "P": "credito"}.get(code)
        if code and row["modalidad"] is None:
            issues.append(observation(row, "modalidad_codigo", "MODALIDAD_DESCONOCIDA", "Modalidad no admitida: usar C o P", code))
        box = row["caja_codigo"]
        if profile.get("departamento_activo") is not False and box and re.fullmatch(profile["caja_patron"], box):
            row["departamento"] = profile["cajas_admitidas"].get(box)
        if profile.get("departamento_activo") is not False and box and row["departamento"] is None:
            issues.append(observation(row, "caja_codigo", "CAJA_DESCONOCIDA", "Código ausente del catálogo del perfil; no se infirió departamento", box))
    row["estado"] = "observado" if any(not issue["tipo"].startswith("AVISO_") for issue in issues) else "valido"
    if row["nivel_registro"] == "detalle":
        row["estado"] = "observado"
        issues.append(observation(row, None, "DETALLE_REFERENCIA", "Línea de producto conservada para vinculación; no es una cabecera consolidable"))
    return row, issues


def mark_exact_repetitions(rows):
    """Aviso de contenido repetido; no elimina, fusiona ni excluye facturas."""
    groups = {}
    for row in rows:
        if row["estado"] != "valido":
            continue
        business = {k: row[k] for k in ("numero_factura", "fecha_factura", "nit_ci", "monto_numeral",
                    "modalidad_codigo", "caja_codigo", "razon_social", "cuf", "anulado")}
        business["adicionales"] = {k: v["valor"] for k, v in row["adicionales"].items()}
        amount = format(row["monto_numeral"], "f")
        business["monto_numeral"] = amount.rstrip("0").rstrip(".") if "." in amount else amount
        signature = json.dumps(business, sort_keys=True, ensure_ascii=False, default=str)
        groups.setdefault(signature, []).append(row)
    issues = []
    for signature, repeated in groups.items():
        if len(repeated) < 2:
            continue
        group_id = "exacto_" + hashlib.sha256(signature.encode()).hexdigest()[:16]
        for row in repeated:
            note = observation(row, None, "AVISO_DUPLICADO_EXACTO", "Contenido de cabecera repetido; fila conservada para revisión")
            note.update(grupo_candidato=group_id, regla="contenido_exacto_v1")
            issues.append(note)
    return issues
