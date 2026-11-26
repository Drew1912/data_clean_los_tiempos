from flask import Blueprint, g, jsonify, request

from .lotes import query, pagination
from ..repositories.auditoria import search
from ..services.errors import InputError

auditoria = Blueprint("auditoria", __name__)


@auditoria.get("/auditoria")
def events():
    if not g.usuario.get("puede_ver_auditoria", False):
        raise InputError("ACCESO_DENEGADO", "Tu usuario no tiene permiso para consultar el historial", 403)
    query(["pagina", "tamano", "desde", "hasta", "accion", "resultado", "usuario", "lote_id"])
    filters = {key:value for key,value in request.args.items() if key not in {"pagina", "tamano"}}
    return jsonify(search(*pagination(), filters))
