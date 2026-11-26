"""Cuentas con roles, sesión firmada y protección CSRF del mismo origen."""
import secrets

from flask import g, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from ..repositories.lotes import connection
from .errors import InputError
from .auditing import record, record_separately

DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))


def initialize_admin():
    # No restablecer ni reemplazar una contraseña existente al reiniciar.
    with connection() as conn:
        created = conn.execute("INSERT INTO usuario(id,nombre,password_hash,puede_ver_auditoria,rol) VALUES (1,'admin',%s,TRUE,'administrador') "
                               "ON CONFLICT (id) DO NOTHING RETURNING id", (generate_password_hash("admin"),)).fetchone()
        if created:
            record(conn, "ADMIN_CREADO")
    return bool(created)


def current_user():
    if type(session.get("usuario_id")) is not int or not 1 <= session['usuario_id'] <= 32767:
        return None
    with connection() as conn:
        user = conn.execute("SELECT id,nombre,activo,version_sesion,puede_ver_auditoria,rol FROM usuario WHERE id=%s", (session['usuario_id'],)).fetchone()
    if not user or not user["activo"] or user["version_sesion"] != session.get("version_sesion"):
        session.clear()
        return None
    return user


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def protect_requests():
    protected = request.blueprint in {"lotes", "auditoria", "usuarios"} or request.endpoint == "auth.logout"
    if protected:
        g.usuario = current_user()
        if not g.usuario:
            raise InputError("SESION_REQUERIDA", "Inicia sesión para continuar", 401)
    if (protected or request.endpoint == "auth.login") and request.method not in {"GET", "HEAD", "OPTIONS"}:
        provided = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf")
        if not expected or not provided.isascii() or not secrets.compare_digest(provided, expected):
            raise InputError("CSRF_INVALIDO", "La sesión de seguridad cambió. Recarga la página y vuelve a intentar", 403)
    if protected and request.endpoint != 'auth.logout':
        from .permissions import authorize
        authorize()


def login_user(username, password):
    with connection() as conn:
        user = conn.execute("SELECT * FROM usuario WHERE lower(nombre)=lower(%s)", (username,)).fetchone()
    # Respuesta uniforme para usuario y contraseña incorrectos.
    valid_password = check_password_hash(user["password_hash"] if user else DUMMY_HASH, password)
    if not user or not user["activo"] or not valid_password:
        record_separately("SESION_INICIADA", result="rechazado", details={"codigo": "CREDENCIALES_INVALIDAS"})
        g.audit_error_handled = True
        raise InputError("CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos", 401)
    record_separately("SESION_INICIADA", user=user)
    g.usuario = user
    session.clear()
    session.permanent = True
    session.update(usuario_id=user["id"], version_sesion=user["version_sesion"])
    from .permissions import public_user
    return {"usuario": public_user(user), "csrf_token": csrf_token()}


def logout_user():
    with connection() as conn:
        conn.execute("UPDATE usuario SET version_sesion=version_sesion+1 WHERE id=%s", (g.usuario["id"],))
        record(conn, "SESION_CERRADA")
    session.clear()
