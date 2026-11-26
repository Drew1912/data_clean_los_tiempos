"""Lectura sin inferencia de columnas ni escritura sobre el original.

Adapta la etapa load_data de scripts/core_processor.py a perfiles explícitos;
evita la inferencia numérica y los descartes silenciosos del prototipo histórico.
"""
import csv
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO, StringIO
import posixpath
import re
import warnings
from zlib import error as CompressionError
from xml.etree import ElementTree as ET
from zipfile import ZipFile, BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl.utils.cell import get_column_letter

from ..services.errors import FileError

MAX_ROWS, MAX_COLUMNS, MAX_SHEETS = 5000, 100, 20
MAX_UNCOMPRESSED = 100 * 1024 * 1024
SHEET_NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def cell(value="", kind="texto", number_format=None):
    result = {"valor": str(value) if value is not None else "", "tipo": kind}
    if number_format is not None:
        result["formato"] = number_format
    return result


def map_headers(headers, profile):
    names = [c["valor"] for c in headers]
    if any(len(name) > 10000 for name in names):
        raise FileError("LIMITE_CELDA", "Un encabezado supera el límite de caracteres")
    normalized = [name.strip() for name in names]
    if any(not name for name in normalized) or len(set(normalized)) != len(names):
        raise FileError("COLUMNAS_INVALIDAS", "Los encabezados deben ser únicos y no estar vacíos")
    mapping = {}
    for canonical, aliases in profile["alias"].items():
        found = [i for i, name in enumerate(normalized) if name in aliases]
        if len(found) > 1:
            raise FileError("COLUMNAS_INVALIDAS", f"Más de una columna corresponde a {canonical}")
        if found:
            mapping[canonical] = names[found[0]]
    if any(name not in normalized for name in profile.get("columnas_firma", [])):
        raise FileError("COLUMNAS_INVALIDAS", "No coincide la firma de columnas del formato")
    missing = [name for name in profile.get("columnas_requeridas", profile["obligatorios"]) if name not in mapping]
    if missing:
        raise FileError("COLUMNAS_INVALIDAS", "Faltan columnas requeridas: " + ", ".join(missing))
    return names, mapping


def build_rows(source_rows, profile, sheet):
    if not source_rows:
        raise FileError("COLUMNAS_INVALIDAS", "No se encontró la fila de encabezado configurada")
    headers = source_rows[0][2]
    while headers and not headers[-1]["valor"].strip() and not any(
            len(values) >= len(headers) and values[len(headers) - 1]["valor"].strip()
            for _, _, values in source_rows[1:]):
        headers = headers[:-1]
    ignored = set()
    if profile.get("permitir_cabeceras_vacias"):
        headers = list(headers)
        for column, h in enumerate(headers):
            if not h["valor"].strip():
                if not any(len(values) > column and values[column]["valor"].strip() for _, _, values in source_rows[1:]):
                    ignored.add(column)
                else:
                    headers[column] = cell("columna_sin_cabecera_" + get_column_letter(column + 1))
    # Solo etiquetas complementarias observadas y autorizadas por el perfil.
    # Nunca desambiguar silenciosamente dos columnas de factura/NIT/importe.
    labels = [h["valor"].strip() for h in headers]
    allowed = set(profile.get("cabeceras_repetidas_admitidas", []))
    for column, label in enumerate(labels):
        if label in allowed and labels.count(label) > 1:
            headers = list(headers)
            headers[column] = cell(label + " [columna " + get_column_letter(column + 1) + "]")
    active = [index for index in range(len(headers)) if index not in ignored]
    names, mapping = map_headers([headers[i] for i in active], profile)
    records = []
    for start, end, values in source_rows[1:]:
        if any(v["valor"].strip() for v in values[len(headers):]):
            raise FileError("COLUMNAS_INVALIDAS", "Hay datos sin encabezado o columnas adicionales al encabezado")
        values = [values[i] if i < len(values) else cell() for i in active]
        if any(len(v["valor"]) > 10000 for v in values):
            raise FileError("LIMITE_CELDA", "Una celda supera el límite de 10.000 caracteres")
        records.append({"hoja": sheet, "fila": start, "linea_fin": end,
                        "original": dict(zip(names, values)), "mapeo": mapping})
    # Solo quitar espacio final; las filas vacías interiores conservan su origen.
    while records and all(not v["valor"].strip() for v in records[-1]["original"].values()):
        records.pop()
    if len(records) > MAX_ROWS:
        raise FileError("LIMITE_FILAS", "El archivo supera 5.000 filas de datos")
    return records


def read_csv(data, profile):
    try:
        decoded = data.decode(profile["encoding"], errors="strict")
        if "\x00" in decoded:
            raise ValueError()
        reader = csv.reader(StringIO(decoded, newline=""), delimiter=profile["delimitador"],
                            quotechar=profile["comillas"], strict=True)
        rows = []
        previous_line = 0
        for i, values in enumerate(reader, 1):
            if len(values) > MAX_COLUMNS or i > MAX_ROWS + profile["fila_encabezado"] + 1:
                raise FileError("LIMITE_ESTRUCTURA", "El CSV supera el límite de filas o columnas")
            rows.append((previous_line + 1, reader.line_num, [cell(v) for v in values]))
            previous_line = reader.line_num
        records = build_rows(rows[profile["fila_encabezado"] - 1:], profile, None)
        return records, [{"nombre": None, "nivel": "cabecera", "estado": "admitida",
                          "fila_encabezado": profile["fila_encabezado"],
                          "mapeo": records[0]["mapeo"] if records else {},
                          "columnas": list(records[0]["original"]) if records else []}], []
    except (UnicodeError, csv.Error, ValueError) as error:
        raise FileError("CSV_INVALIDO", "CSV inválido: comprueba UTF-8, delimitador y comillas del perfil") from error


def numeric_sources(archive, path, header_row=4):
    values = {}
    last_row, last_column = 0, 0
    for _, elem in ET.iterparse(BytesIO(archive.read(path)), events=("end",)):
        if elem.tag == "{" + SHEET_NS["s"] + "}c":
            coordinate = elem.get("r", "")
            if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", coordinate):
                raise FileError("XLSX_INVALIDO", "Coordenada de celda no admitida")
            number = int(re.search(r"[0-9]+", coordinate).group())
            column = column_index_from_string(re.match(r"[A-Z]+", coordinate).group())
            if number > 1048576 or column > 16384:
                raise FileError("XLSX_INVALIDO", "Coordenada fuera de los límites de Excel")
            v = elem.find("s:v", SHEET_NS)
            formula = elem.find("s:f", SHEET_NS)
            inline = elem.findall("s:is//s:t", SHEET_NS)
            has_content = (v is not None and bool(v.text)) or formula is not None or any(t.text for t in inline)
            if not has_content:
                elem.clear()
                continue  # Una celda con estilo, sin valor ni fórmula, no extiende los datos.
            if number > MAX_ROWS + header_row or column > MAX_COLUMNS:
                raise FileError("LIMITE_ESTRUCTURA", "El Excel supera el límite de filas o columnas")
            last_row, last_column = max(last_row, number), max(last_column, column)
            if v is not None and elem.get("t", "n") == "n" and formula is None:
                values[coordinate] = v.text or ""
            elem.clear()
    return values, last_row, last_column


def read_excel(data, profile):
    workbook = None
    try:
        with ZipFile(BytesIO(data)) as archive:
            info = archive.infolist()
            if len(info) > 1000 or sum(p.file_size for p in info) > MAX_UNCOMPRESSED:
                raise FileError("LIMITE_XLSX", "El contenido descomprimido del Excel excede el límite")
            for entry in info:
                if entry.flag_bits & 1 or "vbaproject" in entry.filename.lower() or "externallinks/" in entry.filename.lower():
                    raise FileError("XLSX_NO_ADMITIDO", "No se admiten Excel cifrados, con macros o vínculos externos")
                if entry.filename.endswith((".xml", ".rels")):
                    content = archive.read(entry.filename)
                    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
                        raise FileError("XLSX_NO_ADMITIDO", "El XML contiene declaraciones no admitidas")
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            paths = {}
            for rel in rels:
                target = rel.get("Target", "")
                paths[rel.get("Id")] = (target.lstrip("/") if target.startswith("/")
                                        else posixpath.normpath(posixpath.join("xl", target)))
            book_xml = ET.fromstring(archive.read("xl/workbook.xml"))
            sheet_paths = {}
            for sheet in book_xml.findall("s:sheets/s:sheet", SHEET_NS):
                rel_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                sheet_paths[sheet.get("name")] = paths.get(rel_id)
            workbook = load_workbook(BytesIO(data), read_only=True, data_only=False, keep_links=False)
            if len(workbook.sheetnames) > MAX_SHEETS:
                raise FileError("LIMITE_HOJAS", "El Excel supera 20 hojas")
            records, sheets, issues = [], [], []
            for ws in workbook:
                header_row = profile.get("filas_encabezado", {}).get(ws.title, profile["fila_encabezado"])
                meta = {"nombre": ws.title, "fila_encabezado": header_row}
                if ws.title not in profile["hojas"]:
                    detail = ws.title in profile["hojas_detalle"]
                    sheets.append(dict(meta, nivel="detalle" if detail else "desconocido", estado="excluida"))
                    issues.append({"hoja": ws.title, "tipo": "ESTRUCTURA_DETALLE_FUERA_MVP" if detail else "HOJA_DESCONOCIDA",
                                   "motivo": "Hoja de detalle o no reconocida: no se incorpora como cabecera"})
                    continue
                path = sheet_paths.get(ws.title, "")
                if not path.startswith("xl/worksheets/"):
                    raise FileError("XLSX_INVALIDO", "La hoja no tiene una referencia válida")
                numeric, actual_rows, actual_columns = numeric_sources(archive, path, header_row)
                if (ws.max_row or 0) > MAX_ROWS + header_row or (ws.max_column or 0) > MAX_COLUMNS:
                    issues.append({"hoja": ws.title, "tipo": "AVISO_DIMENSIONES_EXCEL",
                                   "motivo": "La dimensión declarada excede los datos; se leen las celdas con contenido, conservando vacíos interiores"})
                ws.reset_dimensions()
                physical = []
                for row_number, row in enumerate(ws.iter_rows(min_row=header_row,
                        max_row=actual_rows, max_col=max(1, actual_columns)), header_row):
                    values = []
                    for c in row:
                        value = c.value
                        raw = numeric.get(getattr(c, "coordinate", ""))
                        if value is None:
                            values.append(cell())
                        elif isinstance(value, (datetime, date)):
                            item = cell(raw if raw is not None else value.isoformat(), "fecha_excel", c.number_format)
                            item["fecha_iso"] = value.isoformat()
                            if workbook.epoch.year == 1899 and raw is not None and Decimal(raw) == 60:
                                item["fecha_iso"] = "1900-02-29"
                            values.append(item)
                        else:
                            kind = {"f": "formula", "n": "numero", "b": "booleano", "e": "error_excel"}.get(c.data_type, "texto")
                            values.append(cell(raw if raw is not None else value, kind, c.number_format))
                    physical.append((row_number, None, values))
                parsed = build_rows(physical, profile, ws.title)
                records.extend(parsed)
                if parsed and any(" [columna " in name for name in parsed[0]["original"]):
                    issues.append({"hoja": ws.title, "tipo": "AVISO_CABECERAS_REPETIDAS",
                                   "motivo": "Etiquetas complementarias repetidas conservadas con su letra de columna; no se mezclan sus valores"})
                if records and any(name.startswith("columna_sin_cabecera_") for name in records[-1]["original"]):
                    issues.append({"hoja": ws.title, "tipo": "AVISO_COLUMNAS_SIN_CABECERA", "motivo": "Se conservan columnas con datos y sin cabecera bajo un nombre técnico; no se les asigna significado"})
                sheets.append(dict(meta, nivel=profile.get("nivel", "cabecera"), estado="admitida",
                                   mapeo=parsed[0]["mapeo"] if parsed else {},
                                   columnas=list(parsed[0]["original"]) if parsed else []))
            if not any(s["estado"] == "admitida" for s in sheets):
                if any(s["nivel"] == "detalle" for s in sheets):
                    raise FileError("ESTRUCTURA_DETALLE_FUERA_MVP", "Se detectó detalle, pero no una cabecera admitida; no se mezclan líneas de productos")
                raise FileError("HOJA_DESCONOCIDA", "No se encontró la hoja de cabecera definida por el perfil")
            return records, sheets, issues
    except FileError:
        raise
    except (BadZipFile, CompressionError, KeyError, SyntaxError, ValueError, OSError, RuntimeError, TypeError, IndexError, InvalidFileException, NotImplementedError) as error:
        raise FileError("XLSX_INVALIDO", "El archivo no es un Excel válido para el perfil seleccionado") from error
    finally:
        if workbook is not None:
            workbook.close()


def read_invoice(data, profile):
    if profile["extension"] == ".csv":
        return read_csv(data, profile)
    if profile["extension"] == ".xls":
        from .legacy_excel import read_xls
        return read_xls(data, profile)
    # openpyxl puede incluir valores de celdas en warnings (por ejemplo fechas fuera
    # de rango). Convertirlos en aviso genérico, sin exponer datos en logs técnicos.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", UserWarning)
        result = read_excel(data, profile)
    if caught:
        result[2].append({"tipo": "AVISO_LECTURA_XLSX", "motivo": "El lector detectó contenido Excel no interpretable; revisa el original y las observaciones de las filas"})
    return result
