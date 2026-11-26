from flask import Blueprint, jsonify, request

from ..services.authentication import current_user, csrf_token, login_user, logout_user
from ..services.errors import InputError
from ..services.permissions import public_user

auth = Blueprint("auth", __name__)


@auth.get("/auth/sesion")
def status():
    user = current_user()
    return jsonify(usuario=public_user(user) if user else None, csrf_token=csrf_token())


@auth.post("/auth/login")
def login():
    if not request.is_json:
        raise InputError("TIPO_PETICION_INVALIDO", "El inicio de sesión requiere JSON", 415)
    if request.content_length and request.content_length > 4096:
        raise InputError("LIMITE_TAMANO", "Credenciales demasiado largas", 413)
    data = request.get_json()
    if not isinstance(data, dict) or set(data) != {"usuario", "contrasena"} or any(
            not isinstance(v, str) or not 1 <= len(v) <= 200 for v in data.values()):
        raise InputError("CREDENCIALES_INVALIDAS", "Introduce usuario y contraseña", 400)
    return jsonify(login_user(data["usuario"], data["contrasena"]))


@auth.post("/auth/logout")
def logout():
    logout_user()
    return jsonify(estado="sesion_cerrada")
