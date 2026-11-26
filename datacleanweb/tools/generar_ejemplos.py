"""Ejemplos públicos exclusivamente sintéticos para probar carga CSV/Excel."""
import csv
from pathlib import Path

from openpyxl import Workbook

public = Path(__file__).resolve().parents[1] / "frontend/public"
with (public / "ejemplo_facturas.csv").open(encoding="utf-8", newline="") as source:
    rows = list(csv.reader(source, delimiter=";"))
for header in (1, 4):
    book = Workbook()
    sheet = book.active
    sheet.title = "Facturas"
    if header == 4:
        sheet.cell(1, 1, "EJEMPLO SINTÉTICO · No contiene datos empresariales")
    for offset, row in enumerate(rows, header):
        for column, value in enumerate(row, 1):
            sheet.cell(offset, column, value)
    sheet.freeze_panes = f"A{header + 1}"
    target = public / f"ejemplo_facturas_f{header}.xlsx"
    book.save(target)
    book.close()
    print(target.name)
