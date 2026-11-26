from datetime import datetime
from io import BytesIO
import re
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import Workbook
import pytest

from app.profiles import get_profile
from app.readers import invoices
from app.services.cleaning import clean_record
from app.services.errors import FileError
from test_cleaning import HEADER, BASE
from uuid import uuid4


def workbook_data(header_row=1, formula=False, numeric=False, detail=False):
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Facturas"
    headers = HEADER.strip().split(";")
    values = BASE.strip().split(";")
    for row, cells in enumerate([headers, values], header_row):
        for column, value in enumerate(cells, 1): ws.cell(row, column, value)
    if formula: ws.cell(header_row + 1, 4, "=1+2")
    if numeric:
        ws.cell(header_row + 1, 1, 101).number_format = "000000"
        ws.cell(header_row + 1, 3, 12345).number_format = "00000000000"
        ws.cell(header_row + 1, 4, 151.89)
        ws.cell(header_row + 1, 2, datetime(2026, 10, 17)).number_format = "DD/MM/YYYY"
    if detail:
        products = workbook.create_sheet("Detalle")
        products.append(["FACTURA", "PRODUCTO", "CANTIDAD"])
        products.append(["000101", "Línea sintética 1", 1])
        products.append(["000101", "Línea sintética 2", 2])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def change_zip(data, entry, transform):
    output = BytesIO()
    with ZipFile(BytesIO(data)) as source, ZipFile(output, "w", ZIP_DEFLATED) as dest:
        for name in source.namelist():
            content = source.read(name)
            dest.writestr(name, transform(content) if name == entry else content)
    return output.getvalue()


def test_csv_multiline_and_interior_blank_have_physical_origin():
    profile = get_profile("demo_cabecera_csv_f1")
    modified = BASE.replace("  Cliente   Ficticio  ", '"Cliente\nFicticio"')
    rows, _, _ = invoices.read_invoice((HEADER + modified + "\n" + BASE + "\n\n").encode(), profile)
    assert len(rows) == 3
    assert (rows[0]["fila"], rows[0]["linea_fin"]) == (2, 3)
    assert rows[1]["fila"] == 4 and rows[2]["fila"] == 5
    blank, issues = clean_record(rows[1], uuid4(), profile)
    assert blank["estado"] == "observado" and [i["tipo"] for i in issues] == ["FILA_VACIA"]


@pytest.mark.parametrize("content", [b"\xffinvalid", (HEADER + '"unclosed').encode(), (HEADER.replace("NRO FACTURA", "OTRA") + BASE).encode(),
    (HEADER.replace("CONTRATO", "NRO FACTURA") + BASE).encode(), (HEADER.replace("CONTRATO", "NÚMERO DE FACTURA") + BASE).encode()])
def test_invalid_csv_or_structure_has_no_partial_success(content):
    with pytest.raises(FileError): invoices.read_invoice(content, get_profile("demo_cabecera_csv_f1"))


@pytest.mark.parametrize("header", [1, 4])
def test_excel_numeric_identifiers_use_explicit_format_and_date_cells(header):
    profile = get_profile(f"demo_cabecera_xlsx_f{header}")
    rows, _, _ = invoices.read_invoice(workbook_data(header, numeric=True), profile)
    row, issues = clean_record(rows[0], uuid4(), profile)
    assert not issues
    assert row["numero_factura"] == "000101" and row["nit_ci"] == "00000012345"
    assert str(row["monto_numeral"]) == "151.89" and row["fecha_factura"].isoformat() == "2026-10-17"


def test_formula_is_not_evaluated_or_lost():
    profile = get_profile("demo_cabecera_xlsx_f1")
    rows, _, _ = invoices.read_invoice(workbook_data(formula=True), profile)
    row, issues = clean_record(rows[0], uuid4(), profile)
    assert row["original"]["MONTO NUMERAL"]["valor"] == "=1+2"
    assert row["monto_numeral"] is None and row["estado"] == "observado"
    assert issues[0]["campo"] == "monto_numeral"


def test_amount_uses_xml_decimal_not_a_rounded_float():
    data = change_zip(workbook_data(numeric=True), "xl/worksheets/sheet1.xml", lambda xml: xml.replace(b"<v>151.89</v>", b"<v>151.890000000000000001</v>"))
    profile = get_profile("demo_cabecera_xlsx_f1")
    rows, _, _ = invoices.read_invoice(data, profile)
    row, _ = clean_record(rows[0], uuid4(), profile)
    assert row["original"]["MONTO NUMERAL"]["valor"] == "151.890000000000000001"
    assert row["monto_numeral"] is None and row["estado"] == "observado"


def test_wrong_excel_dimension_does_not_hide_content_and_detail_stays_separate():
    data = change_zip(workbook_data(detail=True), "xl/worksheets/sheet1.xml", lambda xml: re.sub(rb'<dimension ref="[^"]+"', b'<dimension ref="A1:A1"', xml))
    rows, sheets, issues = invoices.read_invoice(data, get_profile("demo_cabecera_xlsx_f1"))
    assert len(rows) == 1 and rows[0]["original"]["NRO FACTURA"]["valor"] == "000101"
    assert len(sheets) == 2 and issues[0]["tipo"] == "ESTRUCTURA_DETALLE_FUERA_MVP"


def test_workbook_with_only_detail_is_explicitly_rejected():
    book = Workbook()
    book.active.title = "Detalle"
    book.active.append(["FACTURA", "PRODUCTO", "CANTIDAD"])
    book.active.append(["000101", "Producto ficticio", 1])
    output = BytesIO()
    book.save(output)
    book.close()
    with pytest.raises(FileError) as result:
        invoices.read_invoice(output.getvalue(), get_profile("demo_cabecera_xlsx_f1"))
    assert result.value.code == "ESTRUCTURA_DETALLE_FUERA_MVP"


def test_zip_size_limit_and_doctype_are_rejected(monkeypatch):
    data = workbook_data()
    monkeypatch.setattr(invoices, "MAX_UNCOMPRESSED", 100)
    with pytest.raises(FileError, match="descomprimido"): invoices.read_invoice(data, get_profile("demo_cabecera_xlsx_f1"))
    monkeypatch.setattr(invoices, "MAX_UNCOMPRESSED", 100 * 1024 * 1024)
    data = change_zip(data, "xl/workbook.xml", lambda xml: b'<!DOCTYPE workbook [<!ENTITY x "test">]>' + xml)
    with pytest.raises(FileError, match="declaraciones"): invoices.read_invoice(data, get_profile("demo_cabecera_xlsx_f1"))


def test_library_warning_is_not_logged_with_cell_values(monkeypatch):
    import warnings
    original = invoices.read_excel
    def reader(*args):
        warnings.warn("valor_privado_de_celda", UserWarning)
        return original(*args)
    monkeypatch.setattr(invoices, "read_excel", reader)
    with warnings.catch_warnings(record=True) as outer:
        _, _, notes = invoices.read_invoice(workbook_data(), get_profile("demo_cabecera_xlsx_f1"))
    assert outer == []
    assert notes[-1]["tipo"] == "AVISO_LECTURA_XLSX"
    assert "valor_privado" not in notes[-1]["motivo"]
