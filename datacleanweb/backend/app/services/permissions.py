"""Perfiles iniciales de permisos; no equivalen a roles empresariales validados."""
from flask import g, request

from ..repositories.lotes import checked_id, connection
from .errors import InputError

ALL = {'cargar', 'consultar', 'procesar', 'comparar', 'descargar', 'usuarios', 'auditoria'}
ROLES = {
    'administrador': ('Administrador', ALL),
    'cajas': ('Cajas', {'cargar', 'consultar', 'procesar', 'comparar'}),
    'contabilidad': ('Contabilidad', {'cargar', 'consultar', 'procesar', 'comparar', 'descargar'}),
    'consulta': ('Solo lectura', {'consultar', 'comparar'}),
    'descarga': ('Consulta y descarga', {'consultar', 'descargar'}),
    'carga': ('Solo carga de archivos', {'cargar'}),
}


def permissions(user):
    allowed = set(ROLES.get(user['rol'], ('', set()))[1])
    if not user['puede_ver_auditoria']:
        allowed.discard('auditoria')
    return sorted(allowed)


def public_user(user):
    return {'id': user['id'], 'nombre': user['nombre'], 'rol': user['rol'],
            'puede_ver_auditoria': 'auditoria' in permissions(user), 'permisos': permissions(user)}


def authorize():
    allowed = set(permissions(g.usuario))
    endpoint = request.endpoint
    if request.blueprint == 'usuarios':
        needed = 'usuarios'
    elif request.blueprint == 'auditoria':
        needed = 'auditoria'
    else:
        needed = {'lotes.upload':'cargar', 'lotes.process':'procesar', 'lotes.comparisons':'comparar',
                  'lotes.relations':'comparar', 'lotes.export':'descargar'}.get(endpoint, 'consultar')
        if endpoint in {'lotes.profiles', 'lotes.describe', 'lotes.list_lots'} and 'cargar' in allowed:
            needed = 'cargar'
    if needed not in allowed:
        raise InputError('ACCESO_DENEGADO', 'Tu rol no permite realizar esta acción', 403)
    lot_id = (request.view_args or {}).get('lot_id')
    if lot_id and g.usuario['rol'] != 'administrador':
        with connection() as conn:
            own = conn.execute('SELECT 1 FROM lote WHERE id=%s AND creado_por=%s',
                               (checked_id(lot_id), g.usuario['id'])).fetchone()
        if not own:
            raise InputError('LOTE_NO_ENCONTRADO', 'La carga no existe o no está disponible para tu usuario', 404)
