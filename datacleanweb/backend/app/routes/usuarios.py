import re

from flask import Blueprint, jsonify, request, g
import psycopg
from werkzeug.security import generate_password_hash

from .lotes import query, pagination
from ..repositories.lotes import connection
from ..services.permissions import ROLES, permissions
from ..services.auditing import record
from ..services.errors import InputError

usuarios = Blueprint('usuarios', __name__)


def present(row):
    return {key: row[key] for key in ('id', 'nombre', 'rol', 'activo', 'puede_ver_auditoria')} | {
        'creado_en': row['creado_en'].isoformat(), 'permisos': permissions(row)}


@usuarios.get('/usuarios')
def listing():
    query(['pagina', 'tamano'])
    page, size = pagination()
    with connection() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        total = conn.execute('SELECT COUNT(*) AS n FROM usuario').fetchone()['n']
        rows = conn.execute('SELECT id,nombre,rol,activo,puede_ver_auditoria,creado_en FROM usuario ORDER BY id LIMIT %s OFFSET %s',
                            (size, (page-1)*size)).fetchall()
    return jsonify(datos=[present(row) for row in rows], total=total, pagina=page, tamano=size,
                   roles=[{'codigo': key, 'nombre': label, 'permisos': sorted(allowed)} for key, (label, allowed) in ROLES.items()])


def payload(creating):
    query([])
    if not request.is_json:
        raise InputError('TIPO_PETICION_INVALIDO', 'Envía los datos del usuario en JSON', 415)
    if request.content_length and request.content_length > 4096:
        raise InputError('LIMITE_TAMANO', 'Los datos del usuario superan el tamaño permitido', 413)
    data = request.get_json()
    allowed = {'rol', 'activo', 'contrasena', 'puede_ver_auditoria'} | ({'nombre'} if creating else set())
    if not isinstance(data, dict) or not data or set(data)-allowed:
        raise InputError('USUARIO_INVALIDO', 'Datos de usuario no admitidos')
    if creating and not {'nombre', 'rol', 'contrasena'} <= set(data):
        raise InputError('USUARIO_INVALIDO', 'Indica usuario, rol y contraseña')
    if 'nombre' in data:
        if not isinstance(data['nombre'], str) or not re.fullmatch(r'[a-z][a-z0-9._-]{2,49}', data['nombre']):
            raise InputError('NOMBRE_INVALIDO', 'Usa entre 3 y 50 letras minúsculas, números, punto, guion o guion bajo; empieza por letra')
    if 'rol' in data and (not isinstance(data['rol'], str) or data['rol'] not in ROLES):
        raise InputError('ROL_INVALIDO', 'Selecciona un rol disponible')
    for key in ('activo', 'puede_ver_auditoria'):
        if key in data and type(data[key]) is not bool:
            raise InputError('USUARIO_INVALIDO', 'El estado y el permiso de auditoría deben ser booleanos')
    if 'contrasena' in data and (not isinstance(data['contrasena'], str) or not 8 <= len(data['contrasena']) <= 128 or not data['contrasena'].strip()):
        raise InputError('CONTRASENA_INVALIDA', 'La contraseña nueva debe tener entre 8 y 128 caracteres y no estar vacía')
    return data


@usuarios.post('/usuarios')
def create():
    data = payload(True)
    if data.get('puede_ver_auditoria') and data['rol'] != 'administrador':
        raise InputError('PERMISO_INVALIDO', 'Solo el rol Administrador puede consultar auditoría')
    try:
        with connection() as conn:
            row = conn.execute('INSERT INTO usuario(nombre,password_hash,rol,activo,puede_ver_auditoria) VALUES (%s,%s,%s,%s,%s) RETURNING *',
                (data['nombre'], generate_password_hash(data['contrasena']), data['rol'], data.get('activo', True),
                 data.get('puede_ver_auditoria', data['rol']=='administrador'))).fetchone()
            record(conn, 'USUARIO_CREADO', details={'usuario_afectado': row['id'], 'rol': row['rol'], 'activo': row['activo']})
    except psycopg.errors.UniqueViolation as error:
        raise InputError('USUARIO_EXISTENTE', 'Ese nombre de usuario ya existe', 409) from error
    return jsonify(present(row)), 201


@usuarios.patch('/usuarios/<int:user_id>')
def update(user_id):
    data = payload(False)
    with connection() as conn:
        row = conn.execute('SELECT * FROM usuario WHERE id=%s FOR UPDATE', (user_id,)).fetchone()
        if not row:
            raise InputError('USUARIO_NO_ENCONTRADO', 'El usuario no existe', 404)
        role, active = data.get('rol', row['rol']), data.get('activo', row['activo'])
        if (user_id==1 or user_id==g.usuario['id']) and (role!='administrador' or not active):
            raise InputError('ADMIN_PROTEGIDO', 'No puedes desactivar ni quitar el rol administrador de esta cuenta', 409)
        audit = data.get('puede_ver_auditoria', row['puede_ver_auditoria'] if role==row['rol'] else role=='administrador')
        if audit and role!='administrador':
            raise InputError('PERMISO_INVALIDO', 'Solo el rol Administrador puede consultar auditoría')
        hashed = generate_password_hash(data['contrasena']) if 'contrasena' in data else row['password_hash']
        updated = conn.execute('UPDATE usuario SET rol=%s,activo=%s,puede_ver_auditoria=%s,password_hash=%s,version_sesion=version_sesion+1 WHERE id=%s RETURNING *',
            (role, active, audit, hashed, user_id)).fetchone()
        record(conn, 'USUARIO_ACTUALIZADO', details={'usuario_afectado': user_id, 'rol': role, 'activo': active,
                                                 'credencial_actualizada': 'contrasena' in data})
    return jsonify(present(updated))
