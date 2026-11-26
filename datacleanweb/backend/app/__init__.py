import os
import secrets
from datetime import timedelta
from pathlib import Path

import click
import psycopg

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .routes.health import health
from .routes.lotes import lotes
from .routes.auth import auth
from .routes.auditoria import auditoria
from .routes.usuarios import usuarios
from .services.auditing import record_failed_response
from .services.authentication import protect_requests
from .services.errors import InputError


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE_URL=os.environ.get("DATABASE_URL", ""),
        UPLOAD_ROOT=os.environ.get("UPLOAD_ROOT", str(Path(__file__).resolve().parents[1] / "temporales")),
        MAX_CONTENT_LENGTH=26 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=128 * 1024,
        MAX_FORM_PARTS=25,
        MAX_FILE_BYTES=10 * 1024 * 1024,
        MAX_BATCH_BYTES=25 * 1024 * 1024,
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_NAME="dataclean_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=False,
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        if app.testing:
            app.config["SECRET_KEY"] = secrets.token_hex(32)
        else:
            root = Path(app.config["UPLOAD_ROOT"])
            root.mkdir(parents=True, exist_ok=True)
            key_path = root / ".session-key"
            try:
                with key_path.open("x", encoding="ascii") as handle:
                    handle.write(secrets.token_hex(32))
            except FileExistsError:
                pass
            app.config["SECRET_KEY"] = key_path.read_text(encoding="ascii").strip()
            if len(app.config["SECRET_KEY"]) < 32:
                raise RuntimeError("La clave de sesión local está incompleta")
    app.before_request(protect_requests)
    app.register_blueprint(health, url_prefix="/api/v1")
    app.register_blueprint(lotes, url_prefix="/api/v1")
    app.register_blueprint(auth, url_prefix="/api/v1")
    app.register_blueprint(auditoria, url_prefix="/api/v1")
    app.register_blueprint(usuarios, url_prefix="/api/v1")
    app.after_request(record_failed_response)

    @app.errorhandler(InputError)
    def input_error(error):
        return jsonify(error.payload()), error.status

    @app.errorhandler(psycopg.Error)
    def database_error(error):
        return jsonify(error={"codigo": "DB_NO_DISPONIBLE", "mensaje": "No se pudo completar la operación en la base de datos"}), 503

    @app.errorhandler(OSError)
    def storage_error(error):
        return jsonify(error={"codigo": "ALMACENAMIENTO_NO_DISPONIBLE", "mensaje": "No se pudo acceder al almacenamiento privado"}), 503

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.error("FALLO_INTERNO")
        return jsonify(error={"codigo": "FALLO_INTERNO", "mensaje": "No se pudo completar la operación"}), 500

    @app.cli.command("limpiar-cargas-vencidas")
    def cleanup():
        from .services.importation import cleanup_expired
        click.echo(f"Lotes vencidos eliminados: {cleanup_expired()}")

    @app.cli.command("actualizar-esquema")
    def update_schema():
        with psycopg.connect(app.config["DATABASE_URL"], connect_timeout=3, autocommit=True) as conn:
            for name in ("002_admitir_xls.sql", "003_admin.sql", "004_contrato_sin_departamento.sql", "005_auditoria.sql", "006_usuarios_roles.sql"):
                conn.execute((Path(__file__).resolve().parents[1] / "db" / name).read_text(encoding="utf-8"))
        click.echo("Esquema actualizado: usuarios, roles, modalidad y auditoría; datos conservados")

    @app.cli.command("inicializar-admin")
    def init_admin():
        from .services.authentication import initialize_admin
        click.echo("Administrador de demostración creado" if initialize_admin() else "Administrador ya existe; se conserva su configuración")

    @app.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error={
            "codigo": f"HTTP_{error.code}",
            "mensaje": {404: "Recurso no disponible", 413: "La petición supera el tamaño permitido"}.get(error.code, error.name),
        }), error.code

    return app
