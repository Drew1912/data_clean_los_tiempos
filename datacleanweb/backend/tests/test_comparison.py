from copy import deepcopy
from uuid import uuid4

import pytest

from app.profiles import get_profile
from app.services.comparison import compare_files
from app.services.errors import InputError
from test_upload_api import api, upload, process
from test_material_formats import control_xlsx, siat_xlsx, sac_header_xls


def context():
    files = [{"id": str(uuid4()), "estado": "admitido", "posicion": i, "nombre_original": f"archivo{i}.xlsx",
              "perfil_snapshot": get_profile("material_control_xlsx", "1"),
              "hojas": [{"estado": "admitida", "columnas": ["FACTURA", "NIT", "MONTO", "OTRO"]}]} for i in range(3)]
    config = {"archivo_base_id": files[0]["id"], "archivos": [{"archivo_id": f["id"], "columnas": {
        "numero_factura": "FACTURA", "nit_ci": "NIT", "monto_numeral": "MONTO"}} for f in files], "campos": ["nit_ci", "monto_numeral"]}
    return files, config


def row(file, invoice="1", nit="00123", amount="151.89", number=2, kind="texto"):
    return {"id": str(uuid4()), "archivo_id": file["id"], "hoja": "ENERO", "fila": number, "linea_fin": None,
            "fecha_factura": "2026-01-01", "original": {key: {"valor": value, "tipo": kind if key == "MONTO" else "texto"}
            for key, value in {"FACTURA": invoice, "NIT": nit, "MONTO": amount, "OTRO": "151.89"}.items()}}


def test_invoice_locates_even_when_nit_amount_date_differ_and_union_includes_other_files():
    files, config = context()
    rows = [row(files[0]), row(files[1], nit="999", amount="152"), row(files[2], invoice="2")]
    rows[1]["fecha_factura"] = "2025-01-01"
    result = compare_files(files, rows, config)
    assert len(result["datos"]) == 2
    assert [a["estado"] for a in result["datos"][0]["archivos"]] == ["referencia", "difiere", "no_existe"]
    assert result["datos"][0]["archivos"][1]["campos"]["nit_ci"]["estado"] == "diferente"
    assert result["datos"][1]["archivos"][0]["estado"] == "no_existe"
    assert result["datos"][1]["archivos"][2]["estado"] == "incompleto"


def test_decimal_equivalence_not_rounding_and_selected_columns():
    files, config = context()
    rows = [row(files[0]), row(files[1], amount="151,89"), row(files[2], amount="151.8900001", kind="numero")]
    result = compare_files(files, rows, config)
    assert [a["estado"] for a in result["datos"][0]["archivos"]] == ["referencia", "coincide", "difiere"]
    config["archivos"][2]["columnas"]["monto_numeral"] = "OTRO"
    assert compare_files(files, rows, config)["resumen"]["coincidencia"] == 1
    assert rows[2]["original"]["MONTO"]["valor"] == "151.8900001"


@pytest.mark.parametrize("other,flag", [("missing", "faltante"), ("different", "diferencia"),
                                      ("invalid", "incompleto"), ("duplicate", "ambiguo"),
                                      ("no_column", "incompleto")])
def test_exact_match_with_reference_survives_other_file_issue_and_filters(other, flag):
    files, config = context()
    rows = [row(files[0]), row(files[1], amount="151,89")]
    if other == "different": rows.append(row(files[2], nit="999"))
    if other == "invalid": rows.append(row(files[2], amount=""))
    if other == "duplicate": rows.extend([row(files[2]), row(files[2], number=3)])
    if other == "no_column": config["archivos"][2]["columnas"]["numero_factura"] = None
    original = deepcopy(rows)
    result = compare_files(files, rows, config)
    assert result["resumen"]["coincidencia"] == result["resumen"][flag] == 1
    assert set(result["datos"][0]["estados"]) == {"coincidencia", flag}
    for filter_value in ["coincidencia", flag]:
        filtered = compare_files(files, rows, dict(config, filtro=filter_value))
        assert filtered["total"] == 1 and filtered["datos"][0]["numero_factura"] == "1"
    assert rows == original


def test_multiple_matching_files_count_invoice_once_without_self_match():
    files, config = context()
    rows = [row(file) for file in files] + [row(files[0], invoice="2")]
    result = compare_files(files, rows, config)
    assert result["resumen"]["coincidencia"] == 1
    assert result["datos"][1]["estados"] == ["faltante"]


def test_agreement_between_non_reference_files_needs_unique_complete_reference():
    files, config = context()
    rows = [row(files[1]), row(files[2])]
    for reference in [[], [row(files[0]), row(files[0], number=3)], [row(files[0], amount="")]]:
        assert compare_files(files, rows + reference, config)["resumen"]["coincidencia"] == 0


def test_changing_reference_changes_matching_pairs():
    files, config = context()
    rows = [row(files[0]), row(files[1]), row(files[2], nit="999")]
    assert compare_files(files, rows, config)["resumen"]["coincidencia"] == 1
    config["archivo_base_id"] = files[2]["id"]
    assert compare_files(files, rows, config)["resumen"]["coincidencia"] == 0


@pytest.mark.parametrize("value,kind", [("", "texto"), ("=1+2", "formula"), ("1,234", "texto"), ("NaN", "numero")])
def test_missing_or_invalid_values_never_equal_even_to_same_invalid(value, kind):
    files, config = context()
    rows = [row(file, amount=value, kind=kind) for file in files]
    result = compare_files(files, rows, config)
    assert result["resumen"]["coincidencia"] == 0 and result["resumen"]["incompleto"] == 1


def test_duplicates_are_ambiguous_preserved_even_identical_and_no_column_is_not_absence():
    files, config = context()
    rows = [row(file) for file in files] + [row(files[1], number=3)]
    config["archivos"][2]["columnas"]["numero_factura"] = None
    result = compare_files(files, rows, config)
    cells = result["datos"][0]["archivos"]
    assert cells[1]["estado"] == "ambiguo" and cells[1]["cantidad_encontrada"] == 2
    assert len(cells[1]["registros"]) == 2
    assert cells[2]["estado"] == "sin_columna_factura"
    assert result["resumen"]["faltante"] == 0


def test_preserve_zeros_unless_explicit_for_invoice_nit_zeros_always_distinct():
    files, config = context()
    rows = [row(files[0], invoice="001"), row(files[1]), row(files[2], nit="123")]
    assert compare_files(files, rows, config)["resumen"]["facturas"] == 2
    config["ignorar_ceros_factura"] = True
    result = compare_files(files, rows, config)
    assert result["resumen"]["facturas"] == 1
    assert result["datos"][0]["archivos"][1]["estado"] == "coincide"
    assert result["datos"][0]["archivos"][2]["estado"] == "difiere"


def test_filters_pagination_and_independent_selected_criteria():
    files, config = context()
    rows = [row(f, invoice=str(i), nit=str(n)) for n, f in enumerate(files) for i in range(3)]
    config.update(campos=["monto_numeral"], pagina=2, tamano=1, filtro="coincidencia")
    result = compare_files(files, rows, config)
    assert result["total"] == 3 and len(result["datos"]) == 1
    config["pagina"] = 1
    assert compare_files(files, rows, config)["configuracion_id"] == result["configuracion_id"]


def test_missing_invoice_notice_counts_searchable_rows_and_gives_origin_without_rejecting_file():
    files, config = context()
    rows = [row(f) for f in files] + [row(files[0], invoice="", number=3)]
    result = compare_files(files, rows, config)
    assert result["archivos"][0]["filas_con_factura_comparable"] == 1
    assert result["archivos"][0]["filas_sin_factura_comparable"] == 1
    assert result["filas_sin_clave_muestra"][0]["fila"] == 3
    assert result["resumen"]["coincidencia"] == 1


@pytest.mark.parametrize("mutation", ["foreign", "unknown_column", "duplicate", "no_fields", "bad_page", "reused_column"])
def test_invalid_configuration_rejected(mutation):
    files, config = context()
    if mutation == "foreign": config["archivos"][0]["archivo_id"] = str(uuid4())
    if mutation == "unknown_column": config["archivos"][0]["columnas"]["nit_ci"] = "DROP TABLE"
    if mutation == "duplicate": config["archivos"][1] = deepcopy(config["archivos"][0])
    if mutation == "no_fields": config["campos"] = []
    if mutation == "bad_page": config["pagina"] = True
    if mutation == "reused_column": config["archivos"][0]["columnas"]["nit_ci"] = "FACTURA"
    with pytest.raises(InputError): compare_files(files, [], config)


def test_api_real_formats_configurable_comparison_with_observed_rows_and_missing_amount(api):
    _, client, _, _ = api
    loaded = upload(client, [("control.xlsx", control_xlsx(), "auto"), ("siat.xlsx", siat_xlsx(), "auto"),
                             ("sac.xls", sac_header_xls(invoice="101", amount=None), "auto")]).json
    lot = loaded["lote_id"]
    files = loaded["archivos"]
    assert "MONTO" in files[0]["hojas"][0]["columnas"]
    config = {"archivo_base_id": files[0]["id"], "archivos": [{"archivo_id": f["id"], "columnas": {
        key: f["hojas"][0]["mapeo"].get(key) for key in ["numero_factura", "nit_ci", "monto_numeral"]}} for f in files]}
    path = f"/api/v1/lotes/{lot}/comparaciones"
    assert client.post(path, json=config).status_code == 409
    assert process(client, lot).status_code == 200
    response = client.post(path, json=config)
    assert response.status_code == 200, response.json
    cells = response.json["datos"][0]["archivos"]
    assert [c["estado"] for c in cells] == ["referencia", "coincide", "incompleto"]
    assert response.json["resumen"]["coincidencia"] == response.json["resumen"]["incompleto"] == 1
    assert cells[2]["campos"]["monto_numeral"]["estado"] == "sin_dato"
    other = upload(client, [("other.xlsx", control_xlsx(), "auto")]).json
    config["archivos"][1]["archivo_id"] = other["archivos"][0]["id"]
    assert client.post(path, json=config).status_code == 400
    assert client.post(path, data="{}", content_type="text/plain").status_code == 415
