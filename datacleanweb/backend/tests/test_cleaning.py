from copy import deepcopy
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.profiles import get_profile
from app.readers.invoices import read_invoice, cell
from app.services.cleaning import clean_record, exact_amount, mark_exact_repetitions

PROFILE = get_profile("demo_cabecera_csv_f1")
HEADER = "NRO FACTURA;FCH. FACTURA;NIT/CI;MONTO NUMERAL;C o P;CAJA;RAZÓN SOCIAL;CUF;ANULADO;CONTRATO\n"
BASE = "000101;17/10/2026;00012345001;151.89;C;0C;  Cliente   Ficticio  ;1E123;NO_INTERPRETADO;000042\n"


@pytest.mark.parametrize("raw,expected", [("151.89", "151.89"), ("333,60", "333.60"), ("2.680,00", "2680.00"), ("0.10", "0.10"), ("0", "0")])
def test_decimal_formats_are_exact(raw, expected):
    assert exact_amount(cell(raw), PROFILE) == Decimal(expected)


@pytest.mark.parametrize("raw", ["1,234", "1.234", "10.123", "-1.00", "NaN", "Infinity", "1e10", "1 234,00", "2,680.00"])
def test_doubtful_amounts_are_not_guessed_or_rounded(raw):
    with pytest.raises(ValueError): exact_amount(cell(raw), PROFILE)


def test_normalization_preserves_originals_identifiers_and_complementary_fields():
    source = read_invoice((HEADER + BASE).encode(), PROFILE)[0][0]
    original = deepcopy(source)
    row, issues = clean_record(source, uuid4(), PROFILE)
    assert source == original
    assert not issues and row["estado"] == "valido"
    assert row["numero_factura"] == "000101" and row["nit_ci"] == "00012345001"
    assert row["razon_social"] == "Cliente Ficticio"
    assert row["fecha_factura"] == date(2026, 10, 17)
    assert row["cuf"] == "1E123"  # Texto CUF no se confunde con un número científico.
    assert row["anulado"] == "NO_INTERPRETADO"
    assert row["adicionales"]["CONTRATO"]["valor"] == "000042"
    assert {c["campo"] for c in row["cambios"]} == {"fecha_factura", "razon_social"}


@pytest.mark.parametrize("old,new,field", [("17/10/2026", "30/02/2026", "fecha_factura"), ("151.89", "1,234", "monto_numeral"),
    (";C;0C;", ";X;0C;", "modalidad_codigo"), (";C;0C;", ";C;9C;", "caja_codigo"), ("00012345001", "", "nit_ci")])
def test_invalid_values_are_observed_without_removing_the_row(old, new, field):
    source = read_invoice((HEADER + BASE.replace(old, new)).encode(), PROFILE)[0][0]
    row, issues = clean_record(source, uuid4(), PROFILE)
    assert row["estado"] == "observado" and row["fila"] == 2
    assert any(issue["campo"] == field for issue in issues)
    assert len(row["original"]) == 10


def test_ci_complement_is_preserved_and_not_forced_to_digits():
    source = read_invoice((HEADER + BASE.replace("00012345001", "  0012345 LP  ")).encode(), PROFILE)[0][0]
    row, issues = clean_record(source, uuid4(), PROFILE)
    assert not issues and row["nit_ci"] == "0012345 LP"


def test_optional_anulado_boolean_is_preserved_without_excluding_invoice():
    source = read_invoice((HEADER + BASE).encode(), PROFILE)[0][0]
    source["original"]["ANULADO"] = cell("True", "booleano")
    row, issues = clean_record(source, uuid4(), PROFILE)
    assert row["anulado"] == "True" and row["estado"] == "valido" and not issues


def test_optional_formula_is_not_evaluated_and_does_not_exclude_invoice():
    source = read_invoice((HEADER + BASE).encode(), PROFILE)[0][0]
    source["original"]["CUF"] = cell("=A1", "formula")
    row, issues = clean_record(source, uuid4(), PROFILE)
    assert row["cuf"] == "=A1" and row["estado"] == "valido"
    assert issues[0]["tipo"] == "AVISO_VALOR_NO_INTERPRETADO"


def test_control_characters_in_identifiers_are_observed_not_removed():
    source = read_invoice((HEADER + BASE).encode(), PROFILE)[0][0]
    source["original"]["NIT/CI"] = cell("00012\t345")
    row, issues = clean_record(source, uuid4(), PROFILE)
    assert row["nit_ci"] is None and row["original"]["NIT/CI"]["valor"] == "00012\t345"
    assert issues[0]["campo"] == "nit_ci"


@pytest.mark.parametrize("header,field", [("MONTO NUMERAL", "monto_numeral"), ("NIT/CI", "nit_ci")])
def test_excel_date_cells_are_not_reinterpreted_as_amounts_or_identifiers(header, field):
    source = read_invoice((HEADER + BASE).encode(), PROFILE)[0][0]
    source["original"][header] = dict(cell("46312", "fecha_excel"), fecha_iso="2026-10-17T00:00:00")
    row, issues = clean_record(source, uuid4(), PROFILE)
    assert row[field] is None and row["estado"] == "observado"
    assert issues[0]["campo"] == field


def test_repeated_content_only_warns_and_distinct_cuf_is_not_the_same_content():
    sources = read_invoice((HEADER + BASE + BASE.replace("151.89", "151.890")).encode(), PROFILE)[0]
    first, _ = clean_record(sources[0], uuid4(), PROFILE)
    repeated = deepcopy(first)
    repeated.update(id=uuid4(), archivo_id=uuid4(), fila=9, monto_numeral=Decimal("151.890"))
    # El valor decimal es igual; no se compara una clave NIT+fecha+monto.
    notes = mark_exact_repetitions([first, repeated])
    assert len(notes) == 2 and len({note["grupo_candidato"] for note in notes}) == 1
    assert first["estado"] == repeated["estado"] == "valido"
    repeated["cuf"] = "OTRO_CUF_NO_VALIDADO"
    assert mark_exact_repetitions([first, repeated]) == []
