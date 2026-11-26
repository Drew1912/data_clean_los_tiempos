"""Buscar por factura; comparar columnas elegidas sin usar los valores como llave.

No modifica el lote ni elige ganadores entre filas repetidas. Las comparaciones
son independientes de la clasificación y del estado de limpieza de la factura.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import re
from uuid import UUID

from .cleaning import identifier, exact_amount
from .errors import InputError

ROLES = {"numero_factura", "nit_ci", "monto_numeral"}
FIELDS = {"nit_ci", "monto_numeral"}
FLAGS = ("ambiguo", "faltante", "diferencia", "incompleto", "coincidencia")


def available_columns(file, rows):
    columns = list(dict.fromkeys(column for sheet in file.get("hojas", [])
                                 if sheet.get("estado") == "admitida" for column in sheet.get("columnas", [])))
    for row in rows:
        for column in row["original"]:
            if column not in columns:
                columns.append(column)
    return columns


def validate_config(config, files, rows_by_file):
    if not isinstance(config, dict) or set(config) - {"archivo_base_id", "archivos", "campos", "ignorar_ceros_factura", "pagina", "tamano", "filtro"}:
        raise InputError("COMPARACION_INVALIDA", "Configuración de comparación inválida")
    selected = config.get("archivos")
    fields = config.get("campos", ["nit_ci", "monto_numeral"])
    if not isinstance(fields, list) or not fields or any(not isinstance(f, str) or f not in FIELDS for f in fields) or len(set(fields)) != len(fields):
        raise InputError("CAMPOS_INVALIDOS", "Selecciona NIT/CI, monto numeral o ambos")
    if not isinstance(selected, list) or not 2 <= len(selected) <= 10:
        raise InputError("ARCHIVOS_INVALIDOS", "Selecciona entre dos y diez archivos para comparar")
    available = {str(file["id"]): file for file in files if file["estado"] == "admitido"}
    settings = []
    used = set()
    for source in selected:
        if not isinstance(source, dict) or set(source) != {"archivo_id", "columnas"}:
            raise InputError("COLUMNAS_INVALIDAS", "Cada archivo necesita su selección de columnas")
        try:
            file_id = str(UUID(source["archivo_id"]))
        except (ValueError, TypeError, AttributeError) as error:
            raise InputError("ARCHIVO_INVALIDO", "Identificador de archivo inválido") from error
        if file_id not in available or file_id in used:
            raise InputError("ARCHIVO_INVALIDO", "Los archivos deben pertenecer al lote, estar admitidos y no repetirse")
        used.add(file_id)
        columns = source["columnas"]
        if not isinstance(columns, dict) or set(columns) != ROLES:
            raise InputError("COLUMNAS_INVALIDAS", "Configura las columnas de factura, NIT/CI y monto de cada archivo")
        known = set(available_columns(available[file_id], rows_by_file[file_id]))
        for column in columns.values():
            if column is not None and (not isinstance(column, str) or column not in known):
                raise InputError("COLUMNA_DESCONOCIDA", "La columna seleccionada no pertenece a ese archivo")
        nonempty = [column for column in columns.values() if column is not None]
        if len(nonempty) != len(set(nonempty)):
            raise InputError("COLUMNAS_REPETIDAS", "Factura, NIT/CI y monto deben utilizar columnas distintas")
        settings.append({"archivo_id": file_id, "columnas": deepcopy(columns)})
    try:
        base = str(UUID(config.get("archivo_base_id", "")))
    except (ValueError, TypeError, AttributeError) as error:
        raise InputError("REFERENCIA_INVALIDA", "Elige un archivo de referencia") from error
    if base not in used:
        raise InputError("REFERENCIA_INVALIDA", "El archivo de referencia debe estar incluido en la comparación")
    zero_policy = config.get("ignorar_ceros_factura", False)
    if type(zero_policy) is not bool:
        raise InputError("POLITICA_INVALIDA", "La opción de ceros de factura debe ser booleana")
    page, size, filter_value = config.get("pagina", 1), config.get("tamano", 25), config.get("filtro", "todos")
    if type(page) is not int or type(size) is not int or not 1 <= page <= 1000000 or not 1 <= size <= 100:
        raise InputError("PAGINACION_INVALIDA", "Página positiva y tamaño entre 1 y 100")
    if not isinstance(filter_value, str) or filter_value not in {"todos", *FLAGS}:
        raise InputError("FILTRO_INVALIDO", "Filtro de comparación no admitido")
    return {"archivo_base_id": base, "archivos": settings, "campos": fields,
            "ignorar_ceros_factura": zero_policy, "pagina": page, "tamano": size, "filtro": filter_value}


def selected_value(row, column, field, profile):
    if column is None or column not in row["original"]:
        return {"estado": "sin_columna", "original": None, "valor": None, "motivo": "No se seleccionó una columna disponible para este campo"}
    source = row["original"][column]
    if not isinstance(source, dict):
        source = {"valor": "" if source is None else str(source), "tipo": "texto"}
    raw = source.get("valor", "")
    if not isinstance(raw, str):
        raw = str(raw)
        source = dict(source, valor=raw)
    if not raw.strip():
        return {"estado": "sin_dato", "original": raw, "valor": None, "motivo": "La celda está vacía"}
    try:
        if source.get("tipo") not in {"texto", "numero"}:
            raise ValueError("Tipo de celda no comparable; no se evalúan fórmulas ni se reinterpretan fechas")
        if field == "monto_numeral":
            # Comparar no certifica una regla financiera: un negativo finito puede
            # compararse, sin alterar el estado observado que tenga en limpieza.
            policy = dict(profile, importe_minimo="-Infinity", escala_maxima=100)
            value = exact_amount(source, policy)
        else:
            value = identifier(source)
        return {"estado": "valido", "original": raw, "valor": value, "motivo": None}
    except ValueError as error:
        return {"estado": "invalido", "original": raw, "valor": None, "motivo": str(error)}


def public_value(value):
    return dict(value, valor=str(value["valor"]) if value["valor"] is not None else None)


def compare_files(files, rows, config):
    rows_by_file = defaultdict(list)
    for row in rows:
        rows_by_file[str(row["archivo_id"])].append(row)
    settings = validate_config(config, files, rows_by_file)
    file_by_id = {str(file["id"]): file for file in files}
    indexes, rejected, keys = {}, [], {}
    sources = []
    for selection in settings["archivos"]:
        file_id, columns = selection["archivo_id"], selection["columnas"]
        file, index = file_by_id[file_id], defaultdict(list)
        invalid_count = 0
        for row in rows_by_file[file_id]:
            invoice = selected_value(row, columns["numero_factura"], "numero_factura", file["perfil_snapshot"])
            if invoice["estado"] != "valido":
                if any((v.get("valor", "") if isinstance(v, dict) else str(v or "")).strip() for v in row["original"].values()):
                    invalid_count += 1
                    if len(rejected) < 100:
                        rejected.append({"archivo_id": file_id, "hoja": row["hoja"], "fila": row["fila"], "motivo": invoice["motivo"]})
                continue
            key = invoice["valor"]
            if settings["ignorar_ceros_factura"] and re.fullmatch(r"[0-9]+", key):
                key = key.lstrip("0") or "0"
            keys.setdefault(key, [])
            if invoice["valor"] not in keys[key]:
                keys[key].append(invoice["valor"])
            normalized = {field: selected_value(row, columns[field], field, file["perfil_snapshot"]) for field in settings["campos"]}
            dt = row.get("fecha_factura")
            index[key].append({"id": str(row["id"]), "factura_original": invoice["original"], "factura": invoice["valor"],
                               "fecha_contexto": dt.isoformat() if isinstance(dt, (date, datetime)) else dt,
                               "origen": {"archivo_id": file_id, "archivo": file["nombre_original"], "hoja": row["hoja"],
                                          "fila": row["fila"], "linea_fin": row["linea_fin"]}, "valores": normalized})
        indexes[file_id] = index
        sources.append({"archivo_id": file_id, "nombre": file["nombre_original"], "indice": file["posicion"],
                        "columnas": columns, "es_referencia": file_id == settings["archivo_base_id"],
                        "filas_con_factura_comparable": sum(len(group) for group in index.values()),
                        "filas_sin_factura_comparable": invalid_count, "filas_evaluadas": len(rows_by_file[file_id])})
    output, totals = [], {flag: 0 for flag in FLAGS}
    for key, variants in keys.items():
        reference = indexes[settings["archivo_base_id"]].get(key, [])
        reference_values = reference[0]["valores"] if len(reference) == 1 else None
        row_flags, cells = set(), []
        for source in sources:
            file_id, columns = source["archivo_id"], source["columnas"]
            matches = indexes[file_id].get(key, [])
            fields, flags = {}, set()
            if columns["numero_factura"] is None:
                state, reason = "sin_columna_factura", "No se puede buscar: este archivo no tiene una columna de factura seleccionada"
                flags.add("incompleto")
            elif not matches:
                state, reason = "no_existe", "No se encontró esta factura entre las filas con clave comparable"
                flags.add("faltante")
            elif len(matches) > 1:
                state, reason = "ambiguo", "Hay varias filas para esta factura; no se eligió una ni se sumaron importes"
                flags.add("ambiguo")
            else:
                for field in settings["campos"]:
                    current = matches[0]["valores"][field]
                    ref = reference_values[field] if reference_values else None
                    if current["estado"] != "valido":
                        field_state = current["estado"]
                        flags.add("incompleto")
                    elif source["es_referencia"]:
                        field_state = "referencia"
                    elif ref is None:
                        field_state = "sin_referencia_unica"
                        flags.add("incompleto")
                    elif ref["estado"] != "valido":
                        field_state = "referencia_incompleta"
                        flags.add("incompleto")
                    elif current["valor"] == ref["valor"]:
                        field_state = "igual"
                    else:
                        field_state = "diferente"
                        flags.add("diferencia")
                    fields[field] = dict(public_value(current), estado=field_state,
                                         valor_referencia=str(ref["valor"]) if ref and ref["valor"] is not None else None,
                                         columna=columns[field])
                if "diferencia" in flags:
                    state, reason = "difiere", "La factura existe, pero difieren los campos indicados respecto a la referencia"
                elif "incompleto" in flags:
                    state, reason = "incompleto", "La factura existe, pero falta un dato comparable o una referencia única"
                else:
                    state = "referencia" if source["es_referencia"] else "coincide"
                    reason = "Fila de referencia" if source["es_referencia"] else "Los campos seleccionados coinciden exactamente"
                    # La coincidencia con la referencia no depende de los otros archivos.
                    if not source["es_referencia"]:
                        flags.add("coincidencia")
            row_flags.update(flags)
            previews = [dict(match, valores={f: public_value(v) for f, v in match["valores"].items()}) for match in matches[:50]]
            cells.append({"archivo_id": file_id, "estado": state, "motivo": reason, "cantidad_encontrada": len(matches),
                          "campos": fields, "registros": previews, "muestra_limitada": len(matches) > 50})
        for flag in row_flags:
            totals[flag] += 1
        output.append({"numero_factura": key, "facturas_originales": variants, "estados": [flag for flag in FLAGS if flag in row_flags],
                       "archivos": cells})
    filtered = output if settings["filtro"] == "todos" else [row for row in output if settings["filtro"] in row["estados"]]
    start = (settings["pagina"] - 1) * settings["tamano"]
    digest_settings = {k: v for k, v in settings.items() if k not in {"pagina", "tamano", "filtro"}}
    return {"datos": filtered[start:start + settings["tamano"]], "pagina": settings["pagina"], "tamano": settings["tamano"],
            "total": len(filtered), "resumen": dict(totals, facturas=len(output)), "archivos": sources,
            "configuracion": settings, "filas_sin_clave_muestra": rejected,
            "configuracion_id": hashlib.sha256(json.dumps(digest_settings, sort_keys=True).encode()).hexdigest()[:20]}
