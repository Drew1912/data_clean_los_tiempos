"""BIFF .xls: resultados numéricos originales, formatos e identificación de fórmulas."""
from io import StringIO
import math
import struct

import xlrd
from xlrd.compdoc import CompDoc, CompDocError

from .invoices import cell, build_rows, MAX_ROWS, MAX_COLUMNS, MAX_SHEETS
from ..services.errors import FileError


def formula_locations(data):
    """Localizar FORMULA por hoja BIFF8; no interpretar sus tokens ni ejecutarla."""
    document = CompDoc(data, logfile=StringIO())
    stream = document.get_named_stream("Workbook") or document.get_named_stream("Book")
    if not stream:
        raise FileError("XLS_INVALIDO", "No se encontró el libro BIFF dentro del archivo")
    sheets, positions, offset = [], {}, 0
    # BOUNDSHEET: desplazamiento absoluto y tipo de hoja. Se preserva el orden.
    while offset + 4 <= len(stream):
        sid, length = struct.unpack_from("<HH", stream, offset)
        payload = stream[offset + 4:offset + 4 + length]
        if sid == 0x85 and len(payload) >= 6 and payload[5] == 0:
            sheets.append(struct.unpack_from("<I", payload)[0])
        offset += 4 + length
        if sid == 0x0A:
            break
    for index, start in enumerate(sheets):
        pos, found = start, set()
        while pos + 4 <= len(stream):
            sid, length = struct.unpack_from("<HH", stream, pos)
            if sid in {0x06, 0x206, 0x406} and length >= 4:
                found.add(struct.unpack_from("<HH", stream, pos + 4))
            pos += 4 + length
            if sid == 0x0A:
                break
        positions[index] = found
    return positions


def read_xls(data, profile):
    book = None
    try:
        if not data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
            raise FileError("XLS_INVALIDO", "Se esperaba un Excel binario .xls, no un archivo renombrado")
        formulas = formula_locations(data)
        book = xlrd.open_workbook(file_contents=data, formatting_info=True, logfile=StringIO(), verbosity=0)
        if book.biff_version != 80:
            raise FileError("XLS_NO_ADMITIDO", "Este lector requiere BIFF8, el formato de las muestras revisadas")
        if book.nsheets > MAX_SHEETS:
            raise FileError("LIMITE_HOJAS", "El libro supera el límite de hojas")
        records, sheets, notes = [], [], []
        for index, sheet in enumerate(book.sheets()):
            if sheet.name not in profile["hojas"]:
                notes.append({"hoja": sheet.name, "tipo": "HOJA_DESCONOCIDA", "motivo": "Hoja fuera del perfil elegido"})
                continue
            if sheet.nrows > MAX_ROWS + 4 or sheet.ncols > MAX_COLUMNS:
                raise FileError("LIMITE_ESTRUCTURA", "El XLS supera el límite de filas o columnas")
            physical = []
            for r in range(profile["fila_encabezado"] - 1, sheet.nrows):
                values = []
                for c in range(sheet.ncols):
                    source = sheet.cell(r, c)
                    fmt = book.format_map[book.xf_list[source.xf_index].format_key].format_str
                    if (r, c) in formulas.get(index, set()):
                        item = cell("Fórmula BIFF (no evaluada)", "formula", fmt)
                        item["resultado_almacenado"] = str(source.value)
                    elif source.ctype in {xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK}:
                        item = cell()
                    elif source.ctype in {xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_DATE}:
                        number = source.value
                        if not math.isfinite(number):
                            item = cell(str(number), "error_excel", fmt)
                        else:
                            text = str(int(number)) if number.is_integer() else repr(number)
                            item = cell(text, "numero", fmt)
                            item.update(almacenamiento="BIFF/IEEE754", binario_hex=number.hex())
                            if source.ctype == xlrd.XL_CELL_DATE:
                                item["tipo"] = "fecha_excel"
                                item["fecha_iso"] = ("1900-02-29" if book.datemode == 0 and number == 60
                                                     else xlrd.xldate_as_datetime(number, book.datemode).isoformat())
                    else:
                        kind = {xlrd.XL_CELL_BOOLEAN: "booleano", xlrd.XL_CELL_ERROR: "error_excel"}.get(source.ctype, "texto")
                        item = cell(source.value, kind, fmt)
                    values.append(item)
                physical.append((r + 1, None, values))
            parsed = build_rows(physical, profile, sheet.name)
            if parsed and any(name.startswith("columna_sin_cabecera_") for name in parsed[0]["original"]):
                notes.append({"hoja": sheet.name, "tipo": "AVISO_COLUMNAS_SIN_CABECERA", "motivo": "Se conservan datos sin cabecera en columnas técnicas, sin interpretar su significado"})
            records.extend(parsed)
            sheets.append({"nombre": sheet.name, "nivel": profile["nivel"], "estado": "admitida",
                           "fila_encabezado": profile["fila_encabezado"], "mapeo": parsed[0]["mapeo"] if parsed else {},
                           "columnas": list(parsed[0]["original"]) if parsed else []})
        if not sheets:
            raise FileError("HOJA_DESCONOCIDA", "No se encontró una hoja admitida por el perfil")
        return records, sheets, notes
    except FileError:
        raise
    except (xlrd.XLRDError, CompDocError, ValueError, TypeError, IndexError, KeyError, struct.error, OSError, EOFError) as error:
        raise FileError("XLS_INVALIDO", "No se pudo leer el Excel binario de forma segura") from error
    finally:
        if book:
            book.release_resources()
