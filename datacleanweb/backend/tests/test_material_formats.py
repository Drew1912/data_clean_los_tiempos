from datetime import datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import psycopg
from openpyxl import Workbook
import pytest
import xlwt

from app.profiles import get_profile
from app.readers.invoices import read_invoice
from app.services.cleaning import clean_record
from app.services.errors import FileError
from app.services.matching import find_relations
from test_upload_api import api, upload, process


def sac_header_xls(invoice="000101", amount=151.89, date="17/01/2026", formula=False):
    headers = ["NRO FACTURA", "FCH. FACTURA", "NIT/CI", "RAZON SOCIAL FACTURA", "ESPACIO", "FEC. GRABACION", 1,
               "COD. CLIENTE", "NOMBRE CLIENTE (COD. CLIENTES)", "C ò P", "CAJA", "MONEDA", "COD. ALMACEN",
               "COD. VENDEDOR", "COD. PUNTO DE VENTA", "TC", "GLOSA", "NRO PROFORMA", "ANULADO", "MONTO LITERIAL",
               "ICE TOTAL", "DESCUENTO", "", "", "", "", "", "", "Importe total de la factura", "Cufd -siat", "Codigo envio"]
    values = [invoice, date, 12345001, "Cliente Ficticio", "", date, 999999, "001", "Cliente Ficticio", "C", "0C",
              1, "", "", "", "", "", "", "A", "MONTO EN LETRAS NO INTERPRETADO", 0, 0,
              "", "", "", "", "", "", amount, "CUFD_FICTICIO_NO_ES_CUF", 111]
    book = xlwt.Workbook()
    sheet = book.add_sheet("Hoja1")
    for c, value in enumerate(headers):
        if value != "": sheet.write(0, c, value)
    for c, value in enumerate(values):
        if value is not None: sheet.write(1, c, value)
    if formula:
        # Fórmula en otro registro, no intentar asignar su resultado a un monto válido.
        for c, value in enumerate(values):
            if c != 28: sheet.write(2, c, value)
        sheet.write(2, 28, xlwt.Formula("1+2"))
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def sac_detail_xls():
    book = xlwt.Workbook()
    sheet = book.add_sheet("Hoja1")
    headers = ["Nro FACTURA", "COD. PRODUCTO", "CANTIDAD", "PRECIO UNITARIO", "SUBTOTAL", "CAJA", "PRECIOS LISTA",
               "DESCUENTOS", "ICE", "ANEXO", "IMPORTE TOTAL", "DESC. POR COLUMNA", ""]
    for c, h in enumerate(headers):
        if h: sheet.write(0, c, h)
    for r in (1, 2):
        for c, v in enumerate([101, f"P{r}", r, 10, 10 * r, "0C", 10, 0, 0, "", 10 * r, 0, "dato sin cabecera"]):
            sheet.write(r, c, v)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def control_xlsx(amount=151.89):
    book = Workbook()
    sheet = book.active
    sheet.title = "ENERO"
    sheet.cell(1, 1, "CONTROL FICTICIO")
    for r, row in enumerate([["CONTRATO ", "NIT", "FACTURA", "MONTO", "FECHA", "CLIENTE", "DEPOSITO", "PUBLICACION"],
                              ["000042", 12345001, 101, amount, datetime(2026, 1, 17), "Cliente Ficticio", "", ""]], 4):
        for c, v in enumerate(row, 1): sheet.cell(r, c, v)
    out = BytesIO()
    book.save(out)
    book.close()
    return out.getvalue()


def siat_xlsx():
    book = Workbook()
    sheet = book.active
    sheet.title = "hoja1"
    sheet.append(["FECHA DE LA FACTURA", "Nº DE LA FACTURA", "NIT / CI CLIENTE", "NOMBRE O RAZON SOCIAL",
                  "IMPORTE TOTAL DE LA VENTA", "CODIGO DE AUTORIZACIÓN", "ESTADO", "COMPLEMENTO"])
    sheet.append(["17/01/2026", 101, 12345001, "Cliente Ficticio", 151.89, "AUTORIZACION_FICTICIA", "ESTADO_NO_INTERPRETADO", ""])
    output = BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()


def test_sac_mapping_preserves_unknown_header_and_cufd_and_uses_user_selected_total():
    profile = get_profile("material_sac_cabecera_xls")
    rows, sheets, notes = read_invoice(sac_header_xls(), profile)
    row, errors = clean_record(rows[0], uuid4(), profile)
    assert not errors and row["estado"] == "valido"
    assert str(row["monto_numeral"]) == "151.89"  # No usar G=999999.
    assert row["cuf"] is None and row["anulado"] == "A"
    assert row["adicionales"]["1"]["valor"] == "999999"
    assert row["adicionales"]["Cufd -siat"]["valor"] == "CUFD_FICTICIO_NO_ES_CUF"
    assert sheets[0]["mapeo"]["modalidad_codigo"] == "C ò P"


def test_total_missing_never_falls_back_to_numeric_header_or_literal_amount():
    profile = get_profile("material_sac_cabecera_xls")
    rows, _, _ = read_invoice(sac_header_xls(amount=None), profile)
    row, issues = clean_record(rows[0], uuid4(), profile)
    assert row["monto_numeral"] is None and row["estado"] == "observado"
    assert any(i["campo"] == "monto_numeral" for i in issues)


def test_biff_formula_is_identified_without_evaluation():
    profile = get_profile("material_sac_cabecera_xls")
    rows, _, _ = read_invoice(sac_header_xls(formula=True), profile)
    row, issues = clean_record(rows[1], uuid4(), profile)
    assert row["monto_numeral"] is None and row["estado"] == "observado"
    assert row["original"]["Importe total de la factura"]["tipo"] == "formula"


def test_detail_rows_remain_separate_and_preserve_unnamed_data():
    profile = get_profile("material_sac_detalle_xls")
    rows, _, notes = read_invoice(sac_detail_xls(), profile)
    assert len(rows) == 2 and notes[0]["tipo"] == "AVISO_COLUMNAS_SIN_CABECERA"
    row, issues = clean_record(rows[0], uuid4(), profile)
    assert row["nivel_registro"] == "detalle" and row["estado"] == "observado"
    assert row["monto_numeral"] is None
    assert row["adicionales"]["columna_sin_cabecera_M"]["valor"] == "dato sin cabecera"


def test_control_cleans_existing_fields_without_inferring_modality_from_filename():
    profile = get_profile("material_control_xlsx")
    rows, _, _ = read_invoice(control_xlsx(), profile)
    row, issues = clean_record(rows[0], uuid4(), profile)
    assert row["numero_factura"] == "101" and row["fecha_factura"].isoformat() == "2026-01-17"
    assert row["modalidad"] is None and row["caja_codigo"] is None and row["estado"] == "observado"
    assert {i["campo"] for i in issues} == {"modalidad_codigo", "caja_codigo"}


def test_siat_preserves_authorization_separately_and_does_not_invent_classification():
    profile = get_profile("material_siat_xlsx")
    rows, _, _ = read_invoice(siat_xlsx(), profile)
    row, issues = clean_record(rows[0], uuid4(), profile)
    assert row["fecha_factura"].isoformat() == "2026-01-17" and str(row["monto_numeral"]) == "151.89"
    assert row["cuf"] is None and row["modalidad"] is None
    assert row["adicionales"]["CODIGO DE AUTORIZACIÓN"]["valor"] == "AUTORIZACION_FICTICIA"


def test_automatic_siat_upload_is_visible_despite_missing_caja_and_modality(api):
    _, client, _, _ = api
    response = upload(client, [("siat.xlsx", siat_xlsx(), "auto")])
    assert response.json["archivos"][0]["perfil_id"] == "material_siat_xlsx"
    lot = response.json["lote_id"]
    assert process(client, lot).json["registros"]["observados"] == 1
    assert client.get(f"/api/v1/lotes/{lot}/registros?estado=todos").json["datos"][0]["numero_factura"] == "101"


def test_corrupt_ole_or_renamed_zip_is_a_file_error():
    for data in [b"PK invalid", bytes.fromhex("D0CF11E0A1B11AE1") + b"bad"]:
        with pytest.raises(FileError): read_invoice(data, get_profile("material_sac_cabecera_xls"))


def test_auto_detection_upload_relations_and_view_of_all_records(api):
    _, client, _, dsn = api
    response = upload(client, [("cabeceras.xls", sac_header_xls(), "auto"), ("detalle.xls", sac_detail_xls(), "auto"),
                              ("contado.xlsx", control_xlsx(), "auto")])
    assert response.status_code == 201, response.json
    assert {a["nivel"] for a in response.json["archivos"]} == {"cabecera", "detalle"}
    lot = response.json["lote_id"]
    result = process(client, lot)
    assert result.status_code == 200, result.json
    assert result.json["registros"]["cargados"] == 4
    assert result.json["registros"]["validos"] == 1
    assert client.get(f"/api/v1/lotes/{lot}/registros").json["total"] == 1
    assert client.get(f"/api/v1/lotes/{lot}/registros?estado=todos").json["total"] == 4
    links = client.get(f"/api/v1/lotes/{lot}/relaciones").json
    assert links["total"] == 2
    assert {g["tipo"] for g in links["datos"]} == {"entre_cabeceras", "cabecera_detalle"}
    with psycopg.connect(dsn) as conn:
        # El matching no rellena campos ni elimina líneas de productos.
        assert conn.execute("SELECT COUNT(*) FROM registro").fetchone()[0] == 4
        assert conn.execute("SELECT COUNT(*) FROM registro WHERE modalidad IS NULL").fetchone()[0] == 3


def test_migration_is_repeatable_and_does_not_delete_data(api):
    app, client, _, dsn = api
    lot = upload(client).json["lote_id"]
    for _ in range(2):
        result = app.test_cli_runner().invoke(args=["actualizar-esquema"])
        assert result.exit_code == 0, result.output
    assert client.get(f"/api/v1/lotes/{lot}").status_code == 200


def relation_row(id, file, invoice="000101", nit="001234", date="2026-01-17", box="0C", level="cabecera", amount="10.00"):
    return {"id": id, "numero_factura": invoice, "nit_ci": nit, "fecha_factura": date, "caja_codigo": box, "monto_numeral": amount,
            "nivel_registro": level, "origen": {"archivo_id": file}, "razon_social": None, "modalidad_codigo": None, "cuf": None, "anulado": None}


def test_matching_does_not_use_old_nit_date_amount_key_or_cross_different_dates():
    rows = [relation_row("1", "a"), relation_row("2", "b", invoice="000102"), relation_row("3", "b", date="2025-07-17")]
    assert find_relations(rows)[0] == []


def test_matching_marks_ambiguity_and_preserves_original_invoice_numbers():
    rows = [relation_row("1", "a"), relation_row("2", "b", invoice="101", date="2025-07-17"),
            relation_row("3", "c", invoice="101", date=None, nit=None, level="detalle")]
    groups, _ = find_relations(rows)
    assert len(groups) == 1 and groups[0]["estado"] == "ambiguo"
    assert groups[0]["facturas_originales"] == ["000101", "101"]
    assert rows[0]["numero_factura"] == "000101"


def test_matching_reports_differences_without_merging_or_changing_amounts():
    rows = [relation_row("1", "a"), relation_row("2", "b", amount="11.00", box=None)]
    groups, _ = find_relations(rows)
    assert groups[0]["estado"] == "con_diferencias" and groups[0]["campos_diferentes"] == ["monto_numeral"]
    assert [r["monto_numeral"] for r in rows] == ["10.00", "11.00"]
