import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest
from flask.testing import FlaskClient

from app import create_app
from app.repositories import lotes
from app.services import importation
from test_cleaning import HEADER, BASE
from test_readers import workbook_data

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = (ROOT / "frontend/public/ejemplo_facturas.csv").read_bytes()


class ApiClient(FlaskClient):
    csrf = None

    def open(self, *args, **kwargs):
        if self.csrf and kwargs.get("method", "GET").upper() not in {"GET", "HEAD", "OPTIONS"}:
            kwargs["headers"] = dict(kwargs.get("headers") or {})
            kwargs["headers"].setdefault("X-CSRF-Token", self.csrf)
        return super().open(*args, **kwargs)


@pytest.fixture
def api(tmp_path):
    if not os.environ.get("TEST_DATABASE_URL"):
        pytest.skip("Requiere PostgreSQL de prueba explícito")
    schema = "api_" + uuid4().hex
    dsn = make_conninfo(os.environ["TEST_DATABASE_URL"], options=f"-c search_path={schema},public")
    with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            with psycopg.connect(dsn) as conn:
                ddl = (ROOT / "docs/fase_1/schema_propuesto.sql").read_text(encoding="utf-8").replace("BEGIN;", "").replace("COMMIT;", "")
                conn.execute(ddl)
            app = create_app({"TESTING": True, "DATABASE_URL": dsn, "UPLOAD_ROOT": str(tmp_path / "private")})
            assert app.test_cli_runner().invoke(args=["inicializar-admin"]).exit_code == 0
            app.test_client_class = ApiClient
            client = app.test_client()
            client.csrf = client.get("/api/v1/auth/sesion").json["csrf_token"]
            logged = client.post("/api/v1/auth/login", json={"usuario": "admin", "contrasena": "admin"})
            assert logged.status_code == 200
            client.csrf = logged.json["csrf_token"]
            yield app, client, tmp_path / "private", dsn
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def upload(client, files=None):
    files = files or [("demo.csv", SAMPLE, "demo_cabecera_csv_f1")]
    manifest = {"archivos": [{"indice": i, "perfil_id": profile, "perfil_version": "1"} for i, (_, _, profile) in enumerate(files)]}
    return client.post("/api/v1/lotes", data={"manifiesto": json.dumps(manifest), "archivos": [(BytesIO(data), name) for name, data, _ in files]}, content_type="multipart/form-data")


def process(client, lot):
    return client.post(f"/api/v1/lotes/{lot}/procesamiento")


def test_profiles_include_observed_structures_and_keep_demo_explicit(api):
    response = api[1].get("/api/v1/perfiles")
    assert response.status_code == 200 and len(response.json["datos"]) == 12
    assert sum(p["sintetico"] for p in response.json["datos"]) == 3
    assert not any(p["id"].startswith("referencia") for p in response.json["datos"])


def test_complete_csv_cleaning_flow_retains_errors_originals_and_exact_values(api):
    _, client, private, _ = api
    result = upload(client)
    assert result.status_code == 201, result.json
    lot = result.json["lote_id"]
    assert result.json["puede_procesar"]
    saved = next(private.glob("*.bin"))
    digest = hashlib.sha256(saved.read_bytes()).digest()
    assert client.get(f"/api/v1/lotes/{lot}/registros").status_code == 409
    result = process(client, lot)
    assert result.status_code == 200, result.json
    assert result.json["registros"] == {"cargados": 5, "validos": 3, "observados": 2, "seleccionados": 3, "exportados": 0}
    records = client.get(f"/api/v1/lotes/{lot}/registros").json["datos"]
    assert [r["monto_numeral"] for r in records] == ["151.89", "333.60", "2680.00"]
    assert records[0]["numero_factura"] == "000101" and records[0]["nit_ci"] == "00012345001"
    assert records[0]["razon_social"] == "Cliente Sintético Alfa"
    assert records[0]["adicionales"]["CONTRATO"]["valor"] == "000042"
    notes = client.get(f"/api/v1/lotes/{lot}/observaciones").json["datos"]
    assert len(notes) == 5 and len({n["registro_id"] for n in notes}) == 2
    assert {n["origen"]["fila"] for n in notes} == {5, 6}
    invalid = next(n for n in notes if n["campo"] == "monto_numeral")
    assert invalid["registro_original"]["MONTO NUMERAL"]["valor"] == "1,234"
    assert invalid["registro_normalizado"]["monto_numeral"] is None
    assert process(client, lot).json["registros"]["cargados"] == 5
    assert hashlib.sha256(saved.read_bytes()).digest() == digest


@pytest.mark.parametrize("header", [1, 4])
def test_excel_flow_preserves_origin_and_does_not_merge_detail(api, header):
    _, client, _, _ = api
    result = upload(client, [("demo.xlsx", workbook_data(header, numeric=True, detail=True), f"demo_cabecera_xlsx_f{header}")])
    assert result.status_code == 201 and result.json["puede_procesar"]
    lot = result.json["lote_id"]
    assert process(client, lot).json["registros"]["validos"] == 1
    record = client.get(f"/api/v1/lotes/{lot}/registros").json["datos"][0]
    assert record["origen"]["hoja"] == "Facturas" and record["origen"]["fila"] == header + 1
    assert record["numero_factura"] == "000101"
    notes = client.get(f"/api/v1/lotes/{lot}/observaciones").json["datos"]
    assert len(notes) == 1 and notes[0]["registro_id"] is None
    assert notes[0]["tipo"] == "ESTRUCTURA_DETALLE_FUERA_MVP"


def test_multiple_homonymous_files_and_repetitions_never_remove_rows(api):
    _, client, private, _ = api
    data = (HEADER + BASE).encode()
    result = upload(client, [("igual.csv", data, "demo_cabecera_csv_f1"), ("igual.csv", data, "demo_cabecera_csv_f1")])
    assert result.status_code == 201
    lot = result.json["lote_id"]
    assert len(list(private.glob("*.bin"))) == 2
    response = process(client, lot)
    assert response.json["registros"]["validos"] == 2 and response.json["registros"]["observados"] == 0
    notes = client.get(f"/api/v1/lotes/{lot}/observaciones").json["datos"]
    assert len(notes) == 2 and {n["tipo"] for n in notes} == {"AVISO_DUPLICADO_EXACTO"}
    rows = client.get(f"/api/v1/lotes/{lot}/registros").json["datos"]
    assert len({row["origen"]["archivo_id"] for row in rows}) == 2
    assert all(row["advertencias"] for row in rows)


@pytest.mark.parametrize("name,data,profile", [("bad.xlsx", b"not zip", "demo_cabecera_xlsx_f1"),
    ("bad.csv", b"\xffbroken", "demo_cabecera_csv_f1"), ("datos.txt", b"anything", "demo_cabecera_csv_f1"),
    ("../../peligro.csv", (HEADER + BASE).encode(), "demo_cabecera_csv_f1"),
    ("real.csv", SAMPLE, "referencia_cabecera_csv_f1")])
def test_invalid_sources_are_reported_without_saving_unsafe_files(api, name, data, profile):
    _, client, private, _ = api
    response = upload(client, [(name, data, profile)])
    assert response.status_code == 201 and not response.json["puede_procesar"]
    lot = response.json["lote_id"]
    assert process(client, lot).status_code == 409
    assert client.get(f"/api/v1/lotes/{lot}/observaciones").json["total"] == 1
    assert list(private.glob("*.bin")) == []


def test_partial_batch_keeps_good_source_and_explains_bad_source(api):
    _, client, _, _ = api
    response = upload(client, [("bad.csv", b"wrong", "demo_cabecera_csv_f1"), ("ok.csv", (HEADER + BASE).encode(), "demo_cabecera_csv_f1")])
    assert response.json["puede_procesar"]
    result = process(client, response.json["lote_id"])
    assert result.json["archivos"] == {"recibidos": 2, "admitidos": 1, "rechazados": 1}
    assert result.json["registros"]["cargados"] == 1


def test_manifest_and_transport_limits_are_controlled(api, monkeypatch):
    app, client, _, _ = api
    assert client.post("/api/v1/lotes", json={}).status_code == 415
    assert client.post("/api/v1/lotes", data={"manifiesto": "{"}, content_type="multipart/form-data").status_code == 400
    assert client.post("/api/v1/lotes", data={"manifiesto": "{}"}, content_type="multipart/form-data").status_code == 400
    assert upload(client, [("demo.csv", SAMPLE, "demo_cabecera_csv_f1")] * 11).status_code == 413
    monkeypatch.setitem(app.config, "MAX_FILE_BYTES", 10)
    assert upload(client).status_code == 413


def test_storage_compensation_on_database_failure_does_not_leak_errors(api, monkeypatch):
    _, client, private, _ = api
    def fail(*args): raise psycopg.OperationalError("password=do_not_return")
    monkeypatch.setattr(lotes, "create_lot", fail)
    result = upload(client)
    assert result.status_code == 503 and b"do_not_return" not in result.data
    assert list(private.glob("*.bin")) == []


def test_tampered_original_fails_without_partial_results(api):
    _, client, private, dsn = api
    result = upload(client)
    lot = result.json["lote_id"]
    next(private.glob("*.bin")).write_bytes(b"changed")
    assert process(client, lot).status_code == 409
    assert client.get(f"/api/v1/lotes/{lot}").json["estado"] == "fallido"
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT COUNT(*) FROM registro").fetchone()[0] == 0


def test_processing_database_failure_rolls_back_all_rows(api, monkeypatch):
    _, client, _, dsn = api
    response = upload(client)
    original = importation.clean_record
    calls = 0
    def break_second(*args):
        nonlocal calls
        row, issues = original(*args)
        calls += 1
        if calls == 2: row["numero_factura"] = None
        return row, issues
    monkeypatch.setattr(importation, "clean_record", break_second)
    result = process(client, response.json["lote_id"])
    assert result.status_code == 503
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT COUNT(*) FROM registro").fetchone()[0] == 0
        assert conn.execute("SELECT estado FROM lote").fetchone()[0] == "fallido"


def test_expiry_and_explicit_cleanup_only_remove_expired_lots(api):
    app, client, private, dsn = api
    first = upload(client).json["lote_id"]
    second = upload(client).json["lote_id"]
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE lote SET creado_en=CURRENT_TIMESTAMP - INTERVAL '2 days',vence_en=CURRENT_TIMESTAMP - INTERVAL '1 day' WHERE id=%s", (first,))
    assert client.get(f"/api/v1/lotes/{first}").status_code == 410
    result = app.test_cli_runner().invoke(args=["limpiar-cargas-vencidas"])
    assert result.exit_code == 0 and "1" in result.output
    assert len(list(private.glob("*.bin"))) == 1
    assert client.get(f"/api/v1/lotes/{first}").status_code == 404
    assert client.get(f"/api/v1/lotes/{second}").status_code == 200


def test_api_pagination_filters_and_validation(api):
    _, client, _, _ = api
    lot = upload(client).json["lote_id"]
    process(client, lot)
    endpoint = f"/api/v1/lotes/{lot}/registros"
    page = client.get(endpoint + "?pagina=2&tamano=1").json
    assert page["total"] == 3 and page["datos"][0]["numero_factura"] == "000102"
    assert client.get(endpoint + "?modalidad=contado&departamento=la_paz").json["total"] == 1
    assert client.get(endpoint + "?pagina=0").status_code == 400
    assert client.get(endpoint + "?tamano=9999").status_code == 400
    assert client.get(endpoint + "?modalidad=inventado").status_code == 400
    assert client.get(endpoint + "?otra=1").status_code == 400
    assert client.get("/api/v1/lotes/no_es_uuid").status_code == 400
    assert client.get(f"/api/v1/lotes/{uuid4()}").status_code == 404
