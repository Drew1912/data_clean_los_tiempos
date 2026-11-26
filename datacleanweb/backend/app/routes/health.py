import psycopg
from flask import Blueprint, current_app, jsonify

health = Blueprint("health", __name__)


@health.get("/health")
def check_health():
    try:
        # Sin URL explícita, libpq usa PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD.
        with psycopg.connect(current_app.config["DATABASE_URL"], connect_timeout=3) as conn:
            result = conn.execute(
                "SELECT 1, to_regclass('lote'), to_regclass('archivo'), "
                "to_regclass('registro'), to_regclass('observacion'), to_regclass('usuario'), to_regclass('auditoria')"
            ).fetchone()
        if not result or result[0] != 1 or any(value is None for value in result[1:]):
            return jsonify(estado="error", db="no_disponible"), 503
    except psycopg.Error:
        # No devolver/loguear DSN, credenciales ni texto SQL del fallo.
        return jsonify(estado="error", db="no_disponible"), 503
    return jsonify(estado="ok", db="ok")
