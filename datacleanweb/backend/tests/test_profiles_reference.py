"""Lectura de fixtures de referencia, no lector/limpiador del producto."""
import csv
import json
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures/cabecera_representativa.csv"


def profile(kind):
    return json.loads((ROOT / f"docs/fase_1/perfiles/cabecera_{kind}_v1.json").read_text(encoding="utf-8"))


def test_csv_reference_preserves_identifiers_and_columns():
    p = profile("csv")
    with FIXTURE.open(encoding=p["encoding"], newline="") as handle:
        reader = csv.DictReader(handle, delimiter=p["delimitador"], quotechar=p["comillas"])
        rows = list(reader)
        for field in p["obligatorios"]:
            assert any(alias in reader.fieldnames for alias in p["alias_informe"][field])
    assert rows[0]["NRO FACTURA"] == "000101"
    assert rows[0]["NIT/CI"] == "00012345001"
    assert rows[0]["CONTRATO"] == "000042"
    assert rows[0]["CUF"] == "CUF_DEMO" and rows[0]["ANULADO"] == "NO_INTERPRETADO"
    assert rows[1]["MONTO NUMERAL"] == "2.680,00"
    assert datetime.strptime(rows[0]["FCH. FACTURA"], p["formatos_fecha"][0]).date().isoformat() == "2026-10-17"


@pytest.mark.parametrize("header_row", [1, 4])
def test_excel_reference_header_positions_and_text(tmp_path, header_row):
    p = profile("excel")
    with FIXTURE.open(encoding="utf-8", newline="") as f: rows = list(csv.reader(f, delimiter=";"))
    path = tmp_path / "anonimizado_sintetico.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = p["hoja"]
    for offset, row in enumerate(rows, header_row):
        for column, value in enumerate(row, 1): ws.cell(offset, column, value)
    wb.save(path)
    wb.close()
    loaded = load_workbook(path, read_only=True, data_only=False)
    try:
        values = list(loaded[p["hoja"]].iter_rows(min_row=header_row, values_only=True))
        assert list(values[0]) == rows[0]
        assert values[1][0] == "000101" and values[1][2] == "00012345001"
        assert values[1][-1] == "000042"
    finally: loaded.close()


def test_reference_profiles_do_not_claim_real_catalog_or_validators():
    for kind in ("excel", "csv"):
        p = profile(kind)
        assert not p["habilitado_datos_reales"]
        assert p["cajas_admitidas_confirmadas"] == []
        assert p["cuf_validador"] is None
