"""Auditoría de acciones con metadatos cerrados, sin contenido administrativo."""
import re

from flask import g, has_request_context, request, current_app
import psycopg
from psycopg.types.json import Jsonb

ACTIONS = {
    "ADMIN_CREADO": "Administrador creado", "SESION_INICIADA": "Inicio de sesión",
    "SESION_CERRADA": "Cierre de sesión", "LOTE_CARGADO": "Carga de archivos",
    "CLASIFICACION_CONFIGURADA": "Configuración de clasificación", "LOTE_PROCESADO": "Procesamiento de lote",
    "COMPARACION_EJECUTADA": "Comparación de facturas", "EXCEL_GENERADO": "Excel limpio generado",
    "OBSERVACIONES_GENERADAS": "Reporte de observaciones generado", "LOTE_ELIMINADO": "Purga de lote vencido",
    "AUDITORIA_ACCESO": "Acceso al historial",
    "USUARIO_CREADO": "Usuario creado", "USUARIO_ACTUALIZADO": "Usuario actualizado",
    "USUARIOS_ACCESO": "Acceso a gestión de usuarios",
}
COUNTERS = {"archivos", "admitidos", "rechazados", "registros", "validos", "observados", "cambios", "observaciones", "contratos"}


def record(conn, action, *, lot_id=None, details=None, result="exito", user=None):
    if action not in ACTIONS or result not in {"exito", "rechazado", "error"}:
        raise ValueError("Evento de auditoría no admitido")
    details = details or {}
    for key, value in details.items():
        valid = (key in COUNTERS and type(value) is int and 0 <= value <= 10**9)
        valid |= key == "modalidad" and isinstance(value, str) and value in {"todos", "contado", "credito"}
        valid |= key == "codigo" and isinstance(value, str) and bool(re.fullmatch(r"[A-Z0-9_]{1,64}", value))
        valid |= key == "configuracion" and isinstance(value, str) and bool(re.fullmatch(r"[a-f0-9]{20}", value))
        valid |= key == 'usuario_afectado' and type(value) is int and 1 <= value <= 32767
        valid |= key == 'rol' and isinstance(value, str) and value in {'administrador','cajas','contabilidad','consulta','descarga','carga'}
        valid |= key in {'activo','credencial_actualizada'} and type(value) is bool
        if not valid:
            raise ValueError("Metadato de auditoría no admitido")
    if user is None and has_request_context():
        user = getattr(g, "usuario", None)
    actor = user["nombre"] if user else "No autenticado" if has_request_context() else "Sistema"
    conn.execute("INSERT INTO auditoria(usuario_id,usuario_nombre,accion,resultado,lote_id,detalles) VALUES (%s,%s,%s,%s,%s,%s)",
                 (user["id"] if user else None, actor, action, result, lot_id, Jsonb(details)))


def record_separately(action, **kwargs):
    from ..repositories.lotes import connection
    with connection() as conn:
        record(conn, action, **kwargs)


def record_failed_response(response):
    # Fallos se registran fuera de la transacción rechazada. No leer cuerpos de petición.
    if response.status_code < 400 or getattr(g, "audit_error_handled", False):
        return response
    mapping = {"auth.login": "SESION_INICIADA", "auth.logout": "SESION_CERRADA", "lotes.upload": "LOTE_CARGADO",
               "lotes.process": "LOTE_PROCESADO", "lotes.comparisons": "COMPARACION_EJECUTADA", "auditoria.events": "AUDITORIA_ACCESO"}
    action = mapping.get(request.endpoint)
    if request.blueprint == 'usuarios':
        action = {'usuarios.create':'USUARIO_CREADO', 'usuarios.update':'USUARIO_ACTUALIZADO'}.get(request.endpoint, 'USUARIOS_ACCESO')
    if request.endpoint == "lotes.export":
        action = "EXCEL_GENERADO" if (request.view_args or {}).get("kind") == "limpios" else "OBSERVACIONES_GENERADAS"
    if action:
        try:
            record_separately(action, result="rechazado" if response.status_code < 500 else "error", details={"codigo": f"HTTP_{response.status_code}"})
        except psycopg.Error:
            # Una DB indisponible no permite persistir el intento. Nunca imprimir DSN ni datos.
            current_app.logger.warning("AUDITORIA_NO_DISPONIBLE")
    return response
