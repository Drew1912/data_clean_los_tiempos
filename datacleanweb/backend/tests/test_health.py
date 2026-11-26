import os

import psycopg
import pytest

from app import create_app


def test_database_unavailable_is_controlled():
    app = create_app({"TESTING": True, "DATABASE_URL": "host=127.0.0.1 port=1 dbname=missing user=test password=private"})
    response = app.test_client().get("/api/v1/health")
    assert response.status_code == 503
    assert response.json == {"estado": "error", "db": "no_disponible"}
    assert b"private" not in response.data
    assert response.headers["Cache-Control"] == "no-store"


def test_exports_require_authentication():
    response = create_app({"TESTING": True}).test_client().post("/api/v1/lotes/00000000-0000-0000-0000-000000000000/exportaciones/limpios")
    assert response.status_code == 401
    assert response.is_json


def test_schema_missing_is_not_ready(monkeypatch):
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def execute(self, query): return self
        def fetchone(self): return (1, None, None, None, None)
    monkeypatch.setattr(psycopg, "connect", lambda *args, **kwargs: Connection())
    response = create_app({"TESTING": True}).test_client().get("/api/v1/health")
    assert response.status_code == 503


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Requiere TEST_DATABASE_URL de PostgreSQL de prueba")
def test_real_postgres_health():
    response = create_app({"TESTING": True, "DATABASE_URL": os.environ["TEST_DATABASE_URL"]}).test_client().get("/api/v1/health")
    assert response.status_code == 200
    assert response.json == {"estado": "ok", "db": "ok"}
