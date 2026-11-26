"""Excel privados en memoria: sin truncar datos ni ejecutar fórmulas de entrada."""
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
import json
from uuid import UUID

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.compat.strings import safe_string

from ..repositories import lotes
from .errors import InputError
from .auditing import record

MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CANONICAL = ["numero_factura", "fecha_factura", "nit_ci", "monto_numeral", "razon_social", "modalidad_codigo",
             "caja_codigo", "modalidad", "cuf", "anulado", "estado"]


def safe_cell(sheet, value, header=False):
    if isinstance(value, Decimal):
        # Excel garantiza solo 15 dígitos significativos. Fuera de ellos, texto exacto.
        significant = len(value.as_tuple().digits)
        while significant > 1 and value.as_tuple().digits[significant - 1] == 0:
            significant -= 1
        if significant > 15 or Decimal(safe_string(value)) != value:
            value = str(value)
    if isinstance(value, (UUID, date, datetime)):
        value = value.isoformat() if isinstance(value, (date, datetime)) else str(value)
    if isinstance(value, str):
        if len(value) > 32767 or ILLEGAL_CHARACTERS_RE.search(value):
            raise InputError("CELDA_NO_EXPORTABLE", "Un valor excede los límites de Excel o contiene controles no admitidos; no se truncó ni modificó. Revisa los registros originales", 422)
    cell = WriteOnlyCell(sheet, value=value)
    if isinstance(value, str):
        cell.data_type = "s"  # Incluso =, +, -, @ y errores Excel quedan como texto literal.
        cell.number_format = "@"
    elif isinstance(value, Decimal):
        cell.number_format = "0.00"
    if header:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="163E5C")
    return cell


def table(book, title, headers, rows):
    sheet = book.create_sheet(title)
    sheet.freeze_panes = "A2"
    for i, name in enumerate(headers, 1):
        sheet.column_dimensions[get_column_letter(i)].width = min(44, max(16, len(str(name))+2))
    sheet.append([safe_cell(sheet, name, True) for name in headers])
    count = 0
    for values in rows:
        sheet.append([safe_cell(sheet, value) for value in values])
        count += 1
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{count+1}"
    return count


def build_workbook(lot, files, rows, issues, clean, metadata):
    book = Workbook(write_only=True)
    try:
        by_record = defaultdict(list)
        for note in issues:
            by_record[note["registro_id"]].append(note)
        if clean:
            extras = list(dict.fromkeys(key for row in rows for key in row["adicionales"]))
            headers = CANONICAL + ["archivo_id", "archivo", "hoja", "fila", "linea_fin", "registro_id", "advertencias_duplicidad", "grupo_candidato"] + ["origen__"+key for key in extras]

            def clean_values():
                for row in rows:
                    notes = by_record[row["id"]]
                    duplicated = [n for n in notes if n["grupo_candidato"]]
                    yield [row[k] for k in CANONICAL] + [row["archivo_id"], row["nombre_original"], row["hoja"], row["fila"], row["linea_fin"], row["id"],
                        " | ".join(n["tipo"]+": "+n["motivo"] for n in duplicated), " | ".join(dict.fromkeys(n["grupo_candidato"] for n in duplicated))] + [row["adicionales"].get(key, {}).get("valor") for key in extras]
            table(book, "Registros", headers, clean_values())
        else:
            headers = ["observacion_id", "archivo_id", "archivo", "registro_id", "hoja", "fila", "linea_fin", "campo", "valor_original", "tipo", "motivo", "grupo_candidato", "regla"]
            table(book, "Observaciones", headers, ([note.get("id" if k == "observacion_id" else "nombre_original" if k == "archivo" else k) for k in headers] for note in issues))
        # Todos los valores fuente con su tipo, sin JSON gigantesco por registro.
        selected = rows if clean else [row for row in rows if row["id"] in by_record]
        table(book, "Originales", ["registro_id", "archivo_id", "archivo", "hoja", "fila", "columna", "valor", "metadatos_celda"],
              ([row["id"], row["archivo_id"], row["nombre_original"], row["hoja"], row["fila"], key,
                raw.get("valor") if isinstance(raw, dict) else raw,
                json.dumps({k:v for k,v in raw.items() if k != "valor"}, ensure_ascii=False) if isinstance(raw, dict) else ""]
               for row in selected for key, raw in row["original"].items()))
        table(book, "Cambios", ["registro_id", "archivo", "hoja", "fila", "campo", "original", "normalizado", "regla"],
              ([row["id"], row["nombre_original"], row["hoja"], row["fila"], change.get("campo"), change.get("original"), change.get("normalizado"), change.get("regla")]
               for row in selected for change in row["cambios"]))
        context = [["lote_id", str(lot["id"])], ["tipo", "limpios" if clean else "observaciones"], ["estado_lote", lot["estado"]],
                   *[[key, value] for key, value in metadata.items()], ["registros_exportados", len(rows) if clean else "No modifica el contador de limpios"],
                   ["incidencias_lote", len(issues)], ["regla", "Sin fusionar, sumar ni excluir repeticiones; la selección limpia incluye solo válidos"],
                   ["precision", "Identificadores y originales como texto. Importes con más de 15 dígitos o no serializables sin pérdida como texto exacto; sin redondeo"],
                   ["alcance", "Las observaciones incluyen todo el lote y no reciben filtros administrativos"],
                   ["recepcion", "El contador acredita generación del archivo; no confirma su recepción física en el equipo"]]
        context.extend(["advertencia", warning] for warning in lotes.warnings(files))
        table(book, "Contexto", ["dato", "valor"], context)
        table(book, "Archivos", ["archivo_id", "nombre", "estado", "perfil_id", "perfil_version", "nivel", "columna_contrato"],
              ([f["id"], f["nombre_original"], f["estado"], f["perfil_id"], f["perfil_version"], (f["perfil_snapshot"] or {}).get("nivel"), (f["perfil_snapshot"] or {}).get("columna_contrato")] for f in files))
        output = BytesIO()
        book.save(output)
        return output.getvalue()
    finally:
        # Cerrar streams write-only y retirar los temporales internos de openpyxl,
        # también cuando un valor no puede escribirse o falla la generación.
        for sheet in book.worksheets:
            if not sheet.closed:
                sheet.close()
            writer = getattr(sheet, "_writer", None)
            if writer and isinstance(writer.out, str):
                from pathlib import Path
                if Path(writer.out).exists():
                    writer.cleanup()
        book.close()


def export(lot_id, clean, modality="todos", department="todos"):
    modality, department = lotes.selection(modality, department)
    with lotes.connection() as conn:
        lot, files, rows, issues = lotes.export_snapshot(lot_id, modality, department, clean, conn)
        metadata = {"modalidad": modality if clean else "todos", "departamento": department if clean else "todos",
                    "generado_en": datetime.now(timezone.utc).isoformat()}
        payload = build_workbook(lot, files, rows, issues, clean, metadata)
        if lot["vence_en"] <= datetime.now(timezone.utc):
            raise InputError("LOTE_VENCIDO", "El lote venció durante la generación; realiza una nueva carga", 410)
        if clean:
            metadata["cantidad"] = len(rows)
            lotes.save_export(lot["id"], metadata, conn)
        record(conn, "EXCEL_GENERADO" if clean else "OBSERVACIONES_GENERADAS", lot_id=lot["id"], details={"registros" if clean else "observaciones":len(rows) if clean else len(issues), "modalidad":modality if clean else "todos"})
    # La respuesta solo se crea después del commit; un fallo no actualiza contadores.
    return payload, len(rows) if clean else len(issues), str(lot["id"])
