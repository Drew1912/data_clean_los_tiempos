from datetime import datetime, timezone
import json

import psycopg
from psycopg import sql
import pytest

from app.repositories import lotes
from app.services.auditing import record
from test_upload_api import api, upload, process, HEADER, BASE
from test_auth import login
from test_exportation import clean


def logs(client, **filters):
    result=client.get('/api/v1/auditoria',query_string=filters)
    assert result.status_code==200,result.json
    return result.json


def test_history_requires_session_and_permission_checked_on_every_request(api):
    app,client,_,dsn=api
    assert app.test_client().get('/api/v1/auditoria').status_code==401
    assert logs(client)['total']>=2
    with psycopg.connect(dsn) as conn:conn.execute('UPDATE usuario SET puede_ver_auditoria=FALSE WHERE id=1')
    assert client.get('/api/v1/auditoria').status_code==403
    assert client.get('/api/v1/perfiles').status_code==200
    assert client.get('/api/v1/auth/sesion').json['usuario']['puede_ver_auditoria'] is False
    for method in ['post','patch','delete']:
        assert getattr(client,method)('/api/v1/auditoria',json={}).status_code==405


def test_login_success_failure_and_logout_have_real_identity_without_credentials(api):
    app,client,_,_=api
    anonymous=app.test_client()
    bad=login(anonymous,'PASSWORD_PRIVADO_NO_REGISTRAR')
    assert bad.status_code==401
    failures=logs(client,accion='SESION_INICIADA',resultado='rechazado')['datos']
    assert len(failures)==1 and failures[0]['usuario_id'] is None
    assert failures[0]['usuario_nombre']=='No autenticado'
    succeeded=logs(client,accion='SESION_INICIADA',resultado='exito')['datos']
    assert succeeded[0]['usuario_nombre']=='admin' and succeeded[0]['usuario_id']==1
    assert 'PASSWORD_PRIVADO_NO_REGISTRAR' not in json.dumps(logs(client),ensure_ascii=False)
    assert client.post('/api/v1/auth/logout').status_code==200
    fresh=app.test_client();assert login(fresh).status_code==200
    assert logs(fresh,accion='SESION_CERRADA')['total']==1


def test_upload_configuration_processing_and_exports_are_audited_without_invoice_values(api):
    _,client,_,_=api
    loaded=upload(client,[('NOMBRE_ARCHIVO_PRIVADO.csv',(HEADER+BASE.replace('000042','C-VALOR_CONTRATO_PRIVADO')).encode(),'demo_cabecera_csv_f1')]).json
    lot=loaded['lote_id'];config={'contratos':[{'archivo_id':loaded['archivos'][0]['id'],'columna':'CONTRATO'}]}
    assert client.post(f'/api/v1/lotes/{lot}/procesamiento',json=config).status_code==200
    assert process(client,lot).status_code==200  # Reintento idempotente no inventa un cambio.
    assert clean(client,lot).status_code==200
    assert client.post(f'/api/v1/lotes/{lot}/exportaciones/observaciones').status_code==200
    data=logs(client,lote_id=lot)['datos'];actions=[event['accion'] for event in data]
    assert set(actions)=={'LOTE_CARGADO','CLASIFICACION_CONFIGURADA','LOTE_PROCESADO','EXCEL_GENERADO','OBSERVACIONES_GENERADAS'}
    assert actions.count('LOTE_PROCESADO')==1
    processed=next(event for event in data if event['accion']=='LOTE_PROCESADO')
    assert processed['detalles']['registros']==1 and processed['detalles']['cambios']>=1
    serialized=json.dumps(data,ensure_ascii=False)
    for sensitive in ['NOMBRE_ARCHIVO_PRIVADO','C-VALOR_CONTRATO_PRIVADO','00012345001','1E123','151.89','password_hash','csrf_token']:
        assert sensitive not in serialized
    assert all(event['usuario_nombre']=='admin' for event in data)


def test_failed_write_rolls_back_action_and_audits_error(api,monkeypatch):
    _,client,private,dsn=api
    def fail(*args,**kwargs):raise OSError('NO_MOSTRAR_DETALLE_PRIVADO')
    monkeypatch.setattr(lotes,'record',fail)
    result=upload(client)
    assert result.status_code==503 and b'DETALLE_PRIVADO' not in result.data
    with psycopg.connect(dsn) as conn:assert conn.execute('SELECT count(*) FROM lote').fetchone()[0]==0
    assert not list(private.glob('*.bin'))
    assert logs(client,accion='LOTE_CARGADO',resultado='exito')['total']==0
    assert logs(client,accion='LOTE_CARGADO',resultado='error')['total']==1


def test_expired_lot_cleanup_keeps_history_and_system_actor(api):
    app,client,_,dsn=api
    lot=upload(client).json['lote_id'];process(client,lot)
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE lote SET creado_en=CURRENT_TIMESTAMP-INTERVAL '2 days',vence_en=CURRENT_TIMESTAMP-INTERVAL '1 day' WHERE id=%s",(lot,))
    result=app.test_cli_runner().invoke(args=['limpiar-cargas-vencidas'])
    assert result.exit_code==0,result.output
    assert client.get(f'/api/v1/lotes/{lot}').status_code==404
    data=logs(client,lote_id=lot)['datos']
    assert {'LOTE_CARGADO','LOTE_PROCESADO','LOTE_ELIMINADO'}<=set(event['accion'] for event in data)
    purged=next(event for event in data if event['accion']=='LOTE_ELIMINADO')
    assert purged['usuario_nombre']=='Sistema' and purged['usuario_id'] is None


def test_dates_use_bolivian_days_and_pagination_is_stable(api):
    _,client,_,dsn=api
    with psycopg.connect(dsn) as conn:
        for hour,minute in [(3,59),(4,0)]:
            conn.execute("INSERT INTO auditoria(ocurrido_en,usuario_nombre,accion,resultado) VALUES (%s,'Prueba fechas','AUDITORIA_ACCESO','exito')",(datetime(2026,11,24,hour,minute,tzinfo=timezone.utc),))
        for _ in range(55):conn.execute("INSERT INTO auditoria(usuario_nombre,accion,resultado) VALUES ('Prueba páginas','EXCEL_GENERADO','exito')")
    for day in ['2026-11-23','2026-11-24']:
        assert logs(client,usuario='Prueba fechas',desde=day,hasta=day)['total']==1
    first=logs(client,usuario='Prueba páginas',tamano='25',pagina='1')
    second=logs(client,usuario='Prueba páginas',tamano='25',pagina='2')
    assert first['total']==second['total']==55 and len(first['datos'])==25
    assert not {e['id'] for e in first['datos']} & {e['id'] for e in second['datos']}
    assert logs(client,usuario='Prueba páginas',tamano='25',pagina='1')['datos']==first['datos']


@pytest.mark.parametrize('filters',[{'accion':"' OR TRUE--"},{'resultado':'inventado'},{'desde':'24/11/2026'},{'desde':'2026-11-25','hasta':'2026-11-24'},{'lote_id':'no-uuid'},{'pagina':'0'},{'tamano':'101'},{'desconocido':'x'}])
def test_invalid_filters_are_rejected_without_query_injection(api,filters):
    _,client,_,_=api
    assert client.get('/api/v1/auditoria',query_string=filters).status_code==400


def test_migrations_seed_and_permission_revocation_are_idempotent(api):
    app,client,_,dsn=api
    with psycopg.connect(dsn) as conn:conn.execute('UPDATE usuario SET puede_ver_auditoria=FALSE WHERE id=1')
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=['actualizar-esquema']).exit_code==0
        assert app.test_cli_runner().invoke(args=['inicializar-admin']).exit_code==0
    with psycopg.connect(dsn) as conn:
        assert conn.execute('SELECT puede_ver_auditoria FROM usuario WHERE id=1').fetchone()[0] is False
        assert conn.execute("SELECT count(*) FROM auditoria WHERE accion='ADMIN_CREADO'").fetchone()[0]==1
    assert client.get('/api/v1/auditoria').status_code==403


def test_event_metadata_allowlist_rejects_secrets(api):
    app,_,_,_=api
    with app.app_context(),lotes.connection() as conn:
        with pytest.raises(ValueError):record(conn,'LOTE_CARGADO',details={'contrasena':'NO_REGISTRAR'})
