from io import BytesIO
from pathlib import Path
from uuid import uuid4

from openpyxl import Workbook, load_workbook
import psycopg
import pytest

from test_upload_api import api, upload, process
from test_cleaning import HEADER, BASE
from test_exportation import clean, workbook, records


def control(contracts=("C-0001", "P-0002"), nit=True):
    book=Workbook(); sheet=book.active; sheet.title="FEBRERO"
    sheet.append(["CONTRATO ","NIT","FACTURA","MONTO","FECHA","CLIENTE"])
    for i, contract in enumerate(contracts,1):
        sheet.append([contract,"00012345" if nit else None,f"00010{i}",151.89,"17/02/2026","Cliente ficticio"])
    result=BytesIO();book.save(result);book.close();return result.getvalue()


def prepare(client, contracts=("C-0001","P-0002")):
    loaded=upload(client,[("control.xlsx",control(contracts),"auto")]).json
    config={"contratos":[{"archivo_id":loaded["archivos"][0]["id"],"columna":"CONTRATO "}]}
    return loaded["lote_id"],config


def classify(client,lot,config):
    return client.post(f"/api/v1/lotes/{lot}/procesamiento",json=config)


def test_contract_prefix_classifies_without_caja_or_department_and_exports(api):
    _,client,_,dsn=api
    lot,config=prepare(client)
    result=classify(client,lot,config)
    assert result.status_code==200,result.json
    assert result.json["registros"]["validos"]==2 and result.json["registros"]["observados"]==0
    rows=client.get(f"/api/v1/lotes/{lot}/registros?estado=todos").json["datos"]
    assert [r["modalidad"] for r in rows]==["contado","credito"]
    assert all(r["departamento"] is None and r["caja_codigo"] is None for r in rows)
    assert rows[0]["adicionales"]["CONTRATO "]["valor"]=="C-0001"
    assert any(c["regla"]=="prefijo_contrato_v1:CONTRATO " for c in rows[0]["cambios"])
    assert client.get(f"/api/v1/lotes/{lot}").json["archivos"][0]["columna_contrato"]=="CONTRATO "
    for modality in ["contado","credito"]:
        book=workbook(clean(client,lot,modalidad=modality))
        assert len(records(book))==1 and records(book)[0]["modalidad"]==modality
        assert "departamento" not in next(book["Registros"].values)
        assert records(book,"Archivos")[0]["columna_contrato"]=="CONTRATO "
        book.close()
    # SQL también permite valores válidos sin información departamental.
    with psycopg.connect(dsn) as conn:
        assert conn.execute("SELECT COUNT(*) FROM registro WHERE estado='valido' AND departamento IS NULL AND caja_codigo IS NULL").fetchone()[0]==2


@pytest.mark.parametrize("contract,expected", [(" P-0007 ","credito"),("C0001","contado"),("p0001","credito"),("",None),("000123",None),("X-3",None),("=\"C-1\"",None)])
def test_explicit_contract_rule_and_invalids_do_not_infer_mode(api,contract,expected):
    _,client,_,_=api
    lot,config=prepare(client,[contract])
    result=classify(client,lot,config)
    assert result.status_code==200,result.json
    rows=client.get(f"/api/v1/lotes/{lot}/registros?estado=todos").json["datos"]
    assert rows[0]["modalidad"]==expected
    assert rows[0]["estado"]==("valido" if expected else "observado")
    if expected is None:
        assert any(n["tipo"]=="CONTRATO_INVALIDO" for n in client.get(f"/api/v1/lotes/{lot}/observaciones").json["datos"])


def test_missing_nit_still_observed_and_contract_never_supplies_it(api):
    _,client,_,_=api
    loaded=upload(client,[("control.xlsx",control(nit=False),"auto")]).json
    lot=loaded["lote_id"]
    result=classify(client,lot,{"contratos":[{"archivo_id":loaded["archivos"][0]["id"],"columna":"CONTRATO "}]})
    assert result.status_code==200 and result.json["registros"]["validos"]==0
    rows=client.get(f"/api/v1/lotes/{lot}/registros?estado=todos").json["datos"]
    assert all(r["nit_ci"] is None and r["modalidad"] for r in rows)


def test_no_contract_uses_native_column_and_disabled_department_does_not_validate_box(api):
    _,client,_,_=api
    data=(HEADER+BASE.replace("0C","NO-CATALOGO")).encode()
    loaded=upload(client,[("demo.csv",data,"demo_cabecera_csv_f1")]).json
    result=classify(client,loaded["lote_id"],{"contratos":[{"archivo_id":loaded["archivos"][0]["id"],"columna":None}]})
    assert result.status_code==200 and result.json["registros"]["validos"]==1
    row=client.get(f"/api/v1/lotes/{loaded['lote_id']}/registros").json["datos"][0]
    assert row["modalidad"]=="contado" and row["departamento"] is None and row["caja_codigo"]=="NO-CATALOGO"


def test_contract_selection_has_priority_and_conflict_is_visible(api):
    _,client,_,_=api
    data=(HEADER+BASE.replace("000042","P-001")).encode()
    loaded=upload(client,[("demo.csv",data,"demo_cabecera_csv_f1")]).json
    result=classify(client,loaded["lote_id"],{"contratos":[{"archivo_id":loaded["archivos"][0]["id"],"columna":"CONTRATO"}]})
    assert result.status_code==200 and result.json["registros"]["validos"]==1
    row=client.get(f"/api/v1/lotes/{loaded['lote_id']}/registros").json["datos"][0]
    assert row["modalidad"]=="credito"
    assert any(n["tipo"]=="AVISO_MODALIDAD_CONFLICTIVA" for n in client.get(f"/api/v1/lotes/{loaded['lote_id']}/observaciones").json["datos"])


def test_config_is_validated_before_processing_and_cannot_change_completed_lot(api):
    _,client,_,_=api
    lot,config=prepare(client)
    for bad in [{}, {"contratos":[]}, {"contratos":[{"archivo_id":str(uuid4()),"columna":"CONTRATO "}]},
                {"contratos":[dict(config["contratos"][0],columna="NO_EXISTE")]}, {"contratos":config["contratos"]*2}]:
        assert classify(client,lot,bad).status_code==400
    assert client.get(f"/api/v1/lotes/{lot}").json["estado"]=="cargado"
    assert classify(client,lot,config).status_code==200
    assert classify(client,lot,config).status_code==200
    other={"contratos":[dict(config["contratos"][0],columna=None)]}
    assert classify(client,lot,other).status_code==409


def test_migration_replaces_legacy_required_department_check_preserving_rows(api):
    app,client,_,dsn=api
    # Simula copia anterior con la restricción antigua, antes de la carga nueva.
    with psycopg.connect(dsn) as conn:
        conn.execute("ALTER TABLE registro DROP CONSTRAINT registro_valido_campos_check")
        conn.execute("ALTER TABLE registro ADD CONSTRAINT anterior_campos CHECK (estado<>'valido' OR (fecha_factura IS NOT NULL AND caja_codigo IS NOT NULL AND departamento IS NOT NULL))")
    for _ in range(2):
        assert app.test_cli_runner().invoke(args=["actualizar-esquema"]).exit_code==0
    lot,config=prepare(client)
    assert classify(client,lot,config).json["registros"]["validos"]==2
    with psycopg.connect(dsn) as conn:
        constraints=conn.execute("SELECT conname FROM pg_constraint WHERE conrelid='registro'::regclass").fetchall()
        assert ('anterior_campos',) not in constraints
