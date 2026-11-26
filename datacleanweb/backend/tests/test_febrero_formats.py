from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook
from openpyxl.styles import PatternFill
import pytest

from app.profiles import get_profile, list_profiles
from app.readers.invoices import read_invoice
from app.services.cleaning import clean_record
from app.services.errors import FileError
from test_upload_api import api, upload, process
from test_readers import change_zip


def save(book):
    result = BytesIO()
    book.save(result)
    book.close()
    return result.getvalue()


def control_book(sheets=(("FEBRERO", 1),), phantom=False):
    book = Workbook()
    book.remove(book.active)
    for name, header in sheets:
        sheet = book.create_sheet(name)
        for r, values in enumerate([
            ["CONTRATO ", "NIT", "FACTURA", "MONTO", "FECHA", "CLIENTE"],
            ["0001", "0012345", "000101", 151.89, "17/02/2026", "Cliente ficticio"],
        ], header):
            for c, value in enumerate(values, 1): sheet.cell(r, c, value)
        if phantom:
            sheet.cell(1048576, 12).fill = PatternFill("solid", fgColor="FFFF00")
    return save(book)


def summary_book():
    book = Workbook()
    book.active.title = "febrero corregido"
    book.active.append(["Numero Contrato", "Numero Factura", "Nombre", "Fecha", "Total Factura"])
    book.active.append(["0001", "000101", "Cliente ficticio", "17/02/2026", 151.89])
    return save(book)


def sac_book(detail=False):
    book = Workbook(); sheet = book.active; sheet.title = "Hoja1"
    if detail:
        sheet.append(["Nro FACTURA", "COD. PRODUCTO", "CANTIDAD", "PRECIO UNITARIO", "SUBTOTAL", "CAJA", 0])
        sheet.append(["000101", "PRODUCTO FICTICIO", 1, 10, 10, "0C", "Dato conservado"])
    else:
        sheet.append(["NRO FACTURA", "FCH. FACTURA", "NIT/CI", "RAZON SOCIAL FACTURA", "ESPACIO", "ESPACIO",
                      "C ò P", 0, 0, "CAJA", "MONTO NUMERAL", "CUF", "ANULADO"])
        sheet.append(["000101", "17/02/2026", "0012345", "Cliente ficticio", "UNO", "DOS", "C", "TRES", "CUATRO", "0C", 151.89, "", ""])
    return save(book)


def compatible(data):
    matches = []
    for profile in list_profiles():
        if profile.get("extension") != ".xlsx": continue
        try:
            read_invoice(data, profile)
            matches.append(profile["id"])
        except FileError: pass
    return matches


@pytest.mark.parametrize("sheets", [(("FEBRERO", 1),), (("FEBRERO-TRYSTAR", 1),),
    ((" FEBRERO CONTADO", 1), ("FEBRERO CREDITO", 1)), (("credito", 3), ("contado", 1)),
    (("CREDITO", 4), ("CONTADO", 1))])
def test_control_profiles_preserve_each_sheet_header_row_and_leading_space(sheets):
    data = control_book(sheets)
    assert compatible(data) == ["febrero_control_xlsx"]
    rows, metadata, _ = read_invoice(data, get_profile("febrero_control_xlsx"))
    assert [(r["hoja"], r["fila"]) for r in rows] == [(name, header+1) for name, header in sheets]
    assert [(s["nombre"], s["fila_encabezado"]) for s in metadata] == list(sheets)
    assert all(r["mapeo"]["numero_factura"] == "FACTURA" for r in rows)
    assert all("CONTRATO " in r["original"] for r in rows)


def test_phantom_dimensions_and_blank_styled_cells_do_not_expand_records():
    data = control_book((("CREDITO",4), ("CONTADO",1)), phantom=True)
    rows, sheets, notes = read_invoice(data, get_profile("febrero_control_xlsx"))
    assert len(rows) == 2 and len(sheets) == 2
    assert sum(n["tipo"] == "AVISO_DIMENSIONES_EXCEL" for n in notes) == 2


@pytest.mark.parametrize("payload", [b'<c r="A6000" t="n"><v>1</v></c>', b'<c r="A1048576"><f>1+2</f><v/></c>', b'<c r="CW2" t="inlineStr"><is><t>texto</t></is></c>'])
def test_real_content_beyond_limits_is_still_rejected(payload):
    data = change_zip(control_book(), "xl/worksheets/sheet1.xml", lambda xml: xml.replace(b'</sheetData>', b'<row r="6000">'+payload+b'</row></sheetData>'))
    with pytest.raises(FileError, match="límite"):
        read_invoice(data, get_profile("febrero_control_xlsx"))


def test_sac_repeated_complementary_headers_preserve_each_cell_and_explicit_amount():
    data = sac_book()
    assert compatible(data) == ["febrero_sac_cabecera_xlsx"]
    rows, sheets, notes = read_invoice(data, get_profile("febrero_sac_cabecera_xlsx"))
    original = rows[0]["original"]
    assert [original[key]["valor"] for key in ["ESPACIO [columna E]", "ESPACIO [columna F]", "0 [columna H]", "0 [columna I]"]] == ["UNO", "DOS", "TRES", "CUATRO"]
    assert rows[0]["mapeo"]["monto_numeral"] == "MONTO NUMERAL"
    assert any(n["tipo"] == "AVISO_CABECERAS_REPETIDAS" for n in notes)
    assert len(sheets[0]["columnas"]) == 13
    profile = get_profile("febrero_sac_cabecera_xlsx")
    record, _ = clean_record(rows[0], uuid4(), profile)
    assert str(record["monto_numeral"]) == "151.89"
    assert record["adicionales"]["ESPACIO [columna E]"]["valor"] == "UNO"


def test_repeated_identity_header_is_rejected_instead_of_choosing_a_column():
    data = change_zip(sac_book(), "xl/worksheets/sheet1.xml", lambda xml: xml.replace(b'>ESPACIO<', b'>NIT/CI<', 1))
    with pytest.raises(FileError): read_invoice(data, get_profile("febrero_sac_cabecera_xlsx"))


def test_summary_without_nit_loads_but_does_not_invent_it():
    assert compatible(summary_book()) == ["febrero_resumen_sin_nit_xlsx"]
    profile = get_profile("febrero_resumen_sin_nit_xlsx")
    rows, _, _ = read_invoice(summary_book(), profile)
    record, notes = clean_record(rows[0], uuid4(), profile)
    assert "nit_ci" not in rows[0]["mapeo"] and record["nit_ci"] is None
    assert record["estado"] == "observado"
    assert any(n["campo"] == "nit_ci" for n in notes)


def test_new_xlsx_detail_stays_separate_and_not_an_invoice_total():
    assert compatible(sac_book(detail=True)) == ["febrero_sac_detalle_xlsx"]
    profile = get_profile("febrero_sac_detalle_xlsx")
    rows, sheets, _ = read_invoice(sac_book(detail=True), profile)
    record, _ = clean_record(rows[0], uuid4(), profile)
    assert sheets[0]["nivel"] == "detalle" and record["monto_numeral"] is None
    assert record["adicionales"]["SUBTOTAL"]["valor"] == "10"


def test_auto_upload_processing_and_comparison_of_new_formats(api):
    _, client, _, _ = api
    response = upload(client, [("arbitrario.xlsx", control_book((("CREDITO",4), ("CONTADO",1)), phantom=True), "auto"),
                              ("resumen.xlsx", summary_book(), "auto"), ("cabecera.xlsx", sac_book(), "auto"),
                              ("lineas.xlsx", sac_book(detail=True), "auto")])
    assert response.status_code == 201
    loaded = response.json
    assert all(f["estado"] == "admitido" for f in loaded["archivos"])
    assert loaded["archivos"][1]["hojas"][0]["mapeo"].get("nit_ci") is None
    assert process(client, loaded["lote_id"]).status_code == 200
    files = loaded["archivos"]
    config = {"archivo_base_id": files[2]["id"], "archivos": [{"archivo_id": f["id"], "columnas": {
        key: f["hojas"][0]["mapeo"].get(key) for key in ["numero_factura", "nit_ci", "monto_numeral"]}} for f in files[:3]]}
    path = f'/api/v1/lotes/{loaded["lote_id"]}/comparaciones'
    result = client.post(path, json=config)
    assert result.status_code == 200, result.json
    assert [f["estado"] for f in result.json["datos"][0]["archivos"]] == ["ambiguo", "incompleto", "referencia"]
    config["campos"] = ["monto_numeral"]
    result = client.post(path, json=config)
    assert result.json["datos"][0]["archivos"][1]["estado"] == "coincide"
