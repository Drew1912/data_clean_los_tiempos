from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from itsdangerous import TimestampSigner
import psycopg
from werkzeug.security import check_password_hash

from app import create_app
from test_upload_api import api, upload


def login(client, password="admin"):
    csrf = client.get("/api/v1/auth/sesion").json["csrf_token"]
    return client.post("/api/v1/auth/login", json={"usuario": "admin", "contrasena": password}, headers={"X-CSRF-Token": csrf})


def test_no_session_cannot_read_upload_process_or_compare(api):
    app, _, _, _ = api
    client = app.test_client()
    for path in ["perfiles", f"lotes/{uuid4()}", f"lotes/{uuid4()}/registros"]:
        assert client.get("/api/v1/"+path).status_code == 401
    for path in ["lotes", f"lotes/{uuid4()}/procesamiento", f"lotes/{uuid4()}/comparaciones"]:
        assert client.post("/api/v1/"+path, json={}).status_code == 401
    assert client.get("/api/v1/health").status_code == 200


def test_login_credentials_hash_csrf_and_cookie_attributes(api):
    app, _, _, dsn = api
    client = app.test_client()
    assert client.post("/api/v1/auth/login", json={"usuario":"admin", "contrasena":"admin"}).status_code == 403
    bad = login(client, "incorrecta")
    assert bad.status_code == 401 and bad.json["error"]["mensaje"] == "Usuario o contraseña incorrectos"
    assert client.get("/api/v1/perfiles").status_code == 401
    result = login(client)
    assert result.status_code == 200 and result.json['usuario']['nombre']=='admin'
    assert result.json['usuario']['rol']=='administrador' and result.json['usuario']['puede_ver_auditoria'] is True
    assert set(result.json['usuario']['permisos'])=={'cargar','consultar','procesar','comparar','descargar','usuarios','auditoria'}
    cookie = result.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Expires=" in cookie
    assert client.get("/api/v1/perfiles").status_code == 200
    with psycopg.connect(dsn) as conn:
        hashed, = conn.execute("SELECT password_hash FROM usuario").fetchone()
        assert hashed != "admin" and check_password_hash(hashed, "admin")
    assert "password_hash" not in result.json


def test_csrf_required_for_changes_and_logout_really_revokes_replayed_cookie(api):
    app, client, _, _ = api
    cookie = client.get_cookie("dataclean_session").value
    token = client.csrf
    client.csrf = None
    assert client.post("/api/v1/lotes", json={}).status_code == 403
    assert client.post("/api/v1/auth/logout").status_code == 403
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": token}).status_code == 200
    assert client.get("/api/v1/perfiles").status_code == 401
    replay = app.test_client(); replay.set_cookie("dataclean_session", cookie)
    assert replay.get("/api/v1/perfiles").status_code == 401


def test_disabled_account_rejected_and_lot_creator_recorded(api):
    app, client, _, dsn = api
    loaded = upload(client).json
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT creado_por FROM lote WHERE id=%s", (loaded["lote_id"],)).fetchone()[0] == 1
        conn.execute("UPDATE usuario SET activo=FALSE WHERE id=1")
    assert client.get("/api/v1/perfiles").status_code == 401
    assert login(app.test_client()).status_code == 401


def test_expired_and_tampered_cookie_rejected(api, monkeypatch):
    app, client, _, _ = api
    cookie = client.get_cookie("dataclean_session").value
    forged = app.test_client(); forged.set_cookie("dataclean_session", cookie+"alterado")
    assert forged.get("/api/v1/perfiles").status_code == 401
    # Avanzar exclusivamente el reloj del firmador para probar el vencimiento.
    original = TimestampSigner.get_timestamp
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: original(self)+9*60*60)
    assert client.get("/api/v1/perfiles").status_code == 401


def test_migration_seed_idempotent_and_legacy_lots_retained(api):
    app, client, _, dsn = api
    loaded = upload(client).json
    with psycopg.connect(dsn) as conn:
        original = conn.execute("SELECT password_hash FROM usuario WHERE id=1").fetchone()[0]
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=["actualizar-esquema"]).exit_code == 0
        assert app.test_cli_runner().invoke(args=["inicializar-admin"]).exit_code == 0
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT password_hash FROM usuario WHERE id=1").fetchone()[0] == original
        assert conn.execute("SELECT COUNT(*) FROM lote WHERE id=%s", (loaded["lote_id"],)).fetchone()[0] == 1


def test_secret_is_persistent_between_non_testing_app_restarts(tmp_path):
    config = {"UPLOAD_ROOT": str(tmp_path), "SECRET_KEY": None}
    first = create_app(config); second = create_app(config)
    assert first.secret_key == second.secret_key and len(first.secret_key) >= 32
    assert (tmp_path/".session-key").is_file()
