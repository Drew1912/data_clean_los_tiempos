from copy import deepcopy
import json

import psycopg
import pytest
from werkzeug.security import check_password_hash

from test_upload_api import api, upload, process

PASSWORD='ClaveDePrueba2026'


def create(admin, name='operador', role='contabilidad', **extra):
    return admin.post('/api/v1/usuarios', json=dict(nombre=name,contrasena=PASSWORD,rol=role,**extra))


def login_as(app, name, password=PASSWORD):
    client=app.test_client()
    client.csrf=client.get('/api/v1/auth/sesion').json['csrf_token']
    result=client.post('/api/v1/auth/login', json={'usuario':name,'contrasena':password})
    if result.status_code==200:client.csrf=result.json['csrf_token']
    return client,result


def test_only_administrator_can_manage_accounts_and_passwords_never_leave_hash_storage(api):
    app,admin,_,dsn=api
    result=create(admin)
    assert result.status_code==201,result.json
    uid=result.json['id'];assert uid>1 and result.json['rol']=='contabilidad'
    with psycopg.connect(dsn) as conn:
        hashed=conn.execute('SELECT password_hash FROM usuario WHERE id=%s',(uid,)).fetchone()[0]
        assert hashed!=PASSWORD and check_password_hash(hashed,PASSWORD)
    client,logged=login_as(app,'OPERADOR')
    assert logged.status_code==200 and logged.json['usuario']['id']==uid
    assert client.get('/api/v1/usuarios').status_code==403
    assert create(client,'intruso','administrador').status_code==403
    assert client.patch('/api/v1/usuarios/1',json={'activo':False}).status_code==403
    assert app.test_client().get('/api/v1/usuarios').status_code==401
    listing=admin.get('/api/v1/usuarios').json
    assert listing['total']==2 and len(listing['roles'])==6
    for body in (listing,logged.json,admin.get('/api/v1/auditoria').json):
        text=json.dumps(body)
        assert PASSWORD not in text and 'password_hash' not in text and hashed not in text
    assert create(admin).status_code==409


@pytest.mark.parametrize('role,can_process,can_compare,can_download',[
    ('cajas',True,True,False),('contabilidad',True,True,True),
    ('consulta',False,True,False),('descarga',False,False,True),('carga',False,False,False)])
def test_roles_on_real_owned_lot_and_foreign_lot_are_enforced(api,role,can_process,can_compare,can_download):
    app,admin,_,_=api
    assert create(admin).status_code==201
    client,_=login_as(app,'operador')
    loaded=upload(client).json;lot=loaded['lote_id'];assert process(client,lot).status_code==200
    foreign=upload(admin).json['lote_id']
    assert admin.patch('/api/v1/usuarios/2',json={'rol':role}).status_code==200
    assert client.get('/api/v1/lotes').status_code==401
    client,logged=login_as(app,'operador');assert logged.status_code==200
    for suffix in ('','/registros','/observaciones','/resumen'):
        result=client.get('/api/v1/lotes/'+foreign+suffix)
        assert result.status_code in (403,404)
    assert client.get('/api/v1/lotes').json['total']==1
    assert client.get('/api/v1/lotes/'+lot).status_code==200
    assert client.get('/api/v1/lotes/'+lot+'/registros').status_code==(403 if role=='carga' else 200)
    assert process(client,lot).status_code==(200 if can_process else 403)
    compared=client.post('/api/v1/lotes/'+lot+'/comparaciones',json={})
    assert compared.status_code==(400 if can_compare else 403)
    exported=client.post('/api/v1/lotes/'+lot+'/exportaciones/limpios',json={})
    assert exported.status_code==(200 if can_download else 403)
    report=client.post('/api/v1/lotes/'+lot+'/exportaciones/observaciones')
    assert report.status_code==(200 if can_download else 403)
    assert upload(client).status_code==(201 if role in {'cajas','contabilidad','carga'} else 403)
    assert client.get('/api/v1/auditoria').status_code==403
    assert len(admin.get('/api/v1/lotes').json['datos'])>=2


def test_change_password_disable_and_role_revoke_only_target_sessions_and_keep_originals(api):
    app,admin,_,dsn=api
    assert create(admin).status_code==201
    client,_=login_as(app,'operador');lot=upload(client).json['lote_id'];process(client,lot)
    before=deepcopy(admin.get('/api/v1/lotes/'+lot+'/registros').json)
    assert admin.patch('/api/v1/usuarios/2',json={'contrasena':'NuevaClaveSegura2026'}).status_code==200
    assert client.get('/api/v1/lotes').status_code==401
    assert login_as(app,'operador')[1].status_code==401
    client,logged=login_as(app,'operador','NuevaClaveSegura2026');assert logged.status_code==200
    assert admin.patch('/api/v1/usuarios/2',json={'activo':False}).status_code==200
    assert client.get('/api/v1/lotes').status_code==401
    assert login_as(app,'operador','NuevaClaveSegura2026')[1].status_code==401
    assert admin.get('/api/v1/lotes/'+lot+'/registros').json==before
    with psycopg.connect(dsn) as conn:
        assert conn.execute('SELECT creado_por FROM lote WHERE id=%s',(lot,)).fetchone()[0]==2
    assert admin.patch('/api/v1/usuarios/1',json={'activo':False}).status_code==409
    assert admin.patch('/api/v1/usuarios/1',json={'rol':'consulta'}).status_code==409


@pytest.mark.parametrize('data',[
    {'nombre':'ADMIN'}, {'contrasena':'corta'}, {'contrasena':' '*8}, {'rol':'superusuario'},
    {'activo':'false'}, {'permisos':['usuarios']}, {'puede_ver_auditoria':True}, {'nombre':'a b'}])
def test_bad_user_inputs_and_privilege_injection_are_rejected(api,data):
    result=api[1].post('/api/v1/usuarios',json={'nombre':'operador','rol':'consulta','contrasena':PASSWORD}|data)
    assert result.status_code==400,result.json


def test_user_changes_need_csrf_and_migration_keeps_roles_passwords_and_existing_lots(api):
    app,admin,_,dsn=api
    create(admin);client,_=login_as(app,'operador');lot=upload(client).json['lote_id']
    assert admin.patch('/api/v1/usuarios/2',json={'rol':'carga'}).status_code==200
    admin.csrf=None
    assert create(admin,'otrousuario').status_code==403
    assert admin.patch('/api/v1/usuarios/2',json={'activo':False}).status_code==403
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=['actualizar-esquema']).exit_code==0
        assert app.test_cli_runner().invoke(args=['inicializar-admin']).exit_code==0
    with psycopg.connect(dsn) as conn:
        assert conn.execute('SELECT rol FROM usuario WHERE id=2').fetchone()[0]=='carga'
        assert conn.execute('SELECT creado_por FROM lote WHERE id=%s',(lot,)).fetchone()[0]==2
