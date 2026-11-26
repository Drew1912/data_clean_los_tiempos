from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import hashlib
from pathlib import Path

from openpyxl import load_workbook
import psycopg
from psycopg.types.json import Jsonb
import pytest

from app.services import exportation
from test_upload_api import api, upload, process, SAMPLE
from test_cleaning import HEADER, BASE


def clean(client, lot, **filters):
    return client.post(f"/api/v1/lotes/{lot}/exportaciones/limpios", json=filters)


def workbook(response):
    assert response.status_code == 200, response.json if response.is_json else response.status_code
    assert response.mimetype == exportation.MIME
    assert response.headers["Cache-Control"] == "no-store"
    assert "attachment" in response.headers["Content-Disposition"]
    return load_workbook(BytesIO(response.data), data_only=False)


def records(book, sheet="Registros"):
    rows=list(book[sheet].values)
    return [dict(zip(rows[0], row)) for row in rows[1:]]


def test_clean_export_exact_fields_originals_files_and_latest_counts(api):
    _, client, private, dsn = api
    lot = upload(client).json["lote_id"]
    path = next(private.glob("*.bin")); digest=hashlib.sha256(path.read_bytes()).digest()
    assert clean(client,lot).status_code == 409
    process(client,lot)
    response=clean(client,lot,modalidad="contado",departamento="cochabamba")
    book=workbook(response); rows=records(book)
    assert len(rows)==1
    assert rows[0]["numero_factura"]=="000101" and rows[0]["nit_ci"]=="00012345001"
    assert str(rows[0]["monto_numeral"])=="151.89" and rows[0]["caja_codigo"]=="0C"
    assert rows[0]["origen__CONTRATO"]=="000042"
    assert rows[0]["archivo"]=="demo.csv" and rows[0]["fila"]==2
    assert {"Originales","Cambios","Archivos","Contexto"} <= set(book.sheetnames)
    summary=client.get(f"/api/v1/lotes/{lot}/resumen").json
    assert summary["registros"]["exportados"]==1
    assert summary["ultima_exportacion"]["modalidad"]=="contado"
    assert clean(client,lot).headers["X-Registros-Exportados"]=="3"
    assert client.get(f"/api/v1/lotes/{lot}/resumen?modalidad=contado&departamento=la_paz").json["registros"]["exportados"]==3
    assert hashlib.sha256(path.read_bytes()).digest()==digest
    book.close()


def test_all_filter_combinations_pagination_and_empty_output(api):
    _, client, _, _=api
    lines=[]
    base=BASE.strip().split(";"); header=HEADER.strip().split(";")
    for box in ["1C","1L","1S"]:
        for mode in ["C","P"]:
            fields=base.copy()
            fields[header.index("C o P")]=mode
            fields[header.index("CAJA")]=box
            fields[0]=f"000{len(lines)+1}"
            lines.append(";".join(fields))
    data=(HEADER+"\n".join(lines)+"\n").encode()
    lot=upload(client,[("matriz.csv",data,"demo_cabecera_csv_f1")]).json["lote_id"]; process(client,lot)
    for modality in ["todos","contado","credito"]:
        for department in ["todos","cochabamba","la_paz","santa_cruz"]:
            expected=(6 if department=="todos" else 2)//(1 if modality=="todos" else 2)
            response=clean(client,lot,modalidad=modality,departamento=department)
            book=workbook(response)
            assert len(records(book))==expected
            assert response.headers["X-Registros-Exportados"]==str(expected)
            book.close()
    # Un lote distinto con una única combinación permite selección vacía.
    lot=upload(client,[("solo.csv",(HEADER+BASE).encode(),"demo_cabecera_csv_f1")]).json["lote_id"]; process(client,lot)
    book=workbook(clean(client,lot,modalidad="credito",departamento="santa_cruz"))
    assert records(book)==[] and book["Registros"].max_row==1
    assert client.get(f"/api/v1/lotes/{lot}/resumen").json["registros"]["exportados"]==0
    book.close()


def test_export_includes_more_than_one_page_and_repetitions_warn_without_deletion(api):
    _,client,_,_=api
    data=(HEADER+BASE*30).encode()
    lot=upload(client,[("treinta.csv",data,"demo_cabecera_csv_f1")]).json["lote_id"];process(client,lot)
    assert len(client.get(f"/api/v1/lotes/{lot}/registros?tamano=5").json["datos"])==5
    book=workbook(clean(client,lot)); rows=records(book)
    assert len(rows)==30 and all(r["grupo_candidato"] for r in rows)
    assert all("AVISO_DUPLICADO_EXACTO" in r["advertencias_duplicidad"] for r in rows)
    book.close()


def test_all_observations_include_structure_originals_and_do_not_change_clean_count(api):
    _,client,_,_=api
    lot=upload(client,[("demo.csv",SAMPLE,"demo_cabecera_csv_f1"),("rechazado.csv",b"cabecera desconocida", "auto")]).json["lote_id"]
    before=workbook(client.post(f"/api/v1/lotes/{lot}/exportaciones/observaciones"))
    assert len(records(before,"Observaciones"))==1
    before.close();process(client,lot);clean(client,lot,modalidad="contado",departamento="cochabamba")
    response=client.post(f"/api/v1/lotes/{lot}/exportaciones/observaciones")
    book=workbook(response); issues=records(book,"Observaciones")
    assert len(issues)==6 and response.headers["X-Observaciones-Exportadas"]=="6"
    assert any(r["archivo"]=="rechazado.csv" and r["registro_id"] is None for r in issues)
    assert any(r["valor_original"]=="1,234" for r in issues)
    assert len(records(book,"Originales"))>0
    assert client.get(f"/api/v1/lotes/{lot}/resumen").json["registros"]["exportados"]==1
    book.close()


def test_literal_formula_like_text_cuf_anulado_and_large_money_are_preserved(api):
    _,client,_,dsn=api
    lot=upload(client,[("texto.csv",(HEADER+BASE).encode(),"demo_cabecera_csv_f1")]).json["lote_id"];process(client,lot)
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE registro SET razon_social=%s,cuf=%s,anulado=%s,monto_numeral=%s,adicionales=%s WHERE archivo_id IN(SELECT id FROM archivo WHERE lote_id=%s)",
                     ("=HYPERLINK(\"http://invalid\")","00001234","@ANULADO","123456789012345.67",Jsonb({"EXTRA":{"valor":"=1+2","tipo":"formula"}}),lot))
    book=workbook(clean(client,lot)); row=records(book)[0]
    assert row["monto_numeral"]=="123456789012345.67"
    assert row["cuf"]=="00001234" and row["anulado"]=="@ANULADO" and row["origen__EXTRA"]=="=1+2"
    assert all(cell.data_type!="f" for sheet in book for cells in sheet for cell in cells)
    assert row["razon_social"].startswith("=HYPERLINK")
    book.close()
    # Incluso con 15 dígitos, rechazar el tipo numérico si el serializador
    # convertiría el importe a un valor distinto (no basta contar dígitos).
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE registro SET monto_numeral=%s WHERE estado='valido'",("9.99999999999999",))
    book=workbook(clean(client,lot))
    assert records(book)[0]["monto_numeral"]=="9.99999999999999"
    book.close()


def test_failed_generation_preserves_metadata_and_does_not_truncate(api,monkeypatch):
    _,client,_,dsn=api
    lot=upload(client).json["lote_id"];process(client,lot);clean(client,lot)
    previous=client.get(f"/api/v1/lotes/{lot}/resumen").json["ultima_exportacion"]
    original=exportation.build_workbook
    def fail(*args):raise OSError("no mostrar ruta privada")
    monkeypatch.setattr(exportation,"build_workbook",fail)
    result=clean(client,lot)
    assert result.status_code==503 and b"ruta privada" not in result.data
    assert client.get(f"/api/v1/lotes/{lot}/resumen").json["ultima_exportacion"]==previous
    monkeypatch.setattr(exportation,"build_workbook",original)
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE registro SET adicionales=%s WHERE estado='valido'",(Jsonb({"LARGO":{"valor":"x"*32768,"tipo":"texto"}}),))
    assert clean(client,lot).status_code==422
    assert client.get(f"/api/v1/lotes/{lot}/resumen").json["ultima_exportacion"]==previous


@pytest.mark.parametrize("filters",[{"modalidad":[]},{"departamento":"inventado"},{"pagina":1},None])
def test_invalid_filter_requests_are_rejected(api,filters):
    _,client,_,_=api
    lot=upload(client).json["lote_id"]
    result=client.post(f"/api/v1/lotes/{lot}/exportaciones/limpios",json=filters,content_type="application/json")
    assert result.status_code==400
    assert client.post(f"/api/v1/lotes/{lot}/exportaciones/observaciones",json={}).status_code==400


def test_expiry_session_csrf_and_unknown_lot_are_enforced(api):
    app,client,_,dsn=api
    lot=upload(client).json["lote_id"];process(client,lot)
    assert app.test_client().post(f"/api/v1/lotes/{lot}/exportaciones/limpios",json={}).status_code==401
    csrf=client.csrf;client.csrf=None
    assert clean(client,lot).status_code==403
    client.csrf=csrf
    with psycopg.connect(dsn) as conn:
        conn.execute("UPDATE lote SET creado_en=CURRENT_TIMESTAMP-INTERVAL '2 days',vence_en=CURRENT_TIMESTAMP-INTERVAL '1 day' WHERE id=%s",(lot,))
    assert clean(client,lot).status_code==410
    assert client.post(f"/api/v1/lotes/{lot}/exportaciones/observaciones").status_code==410


def test_concurrent_exports_record_one_complete_latest_result(api):
    app,client,_,_=api
    lot=upload(client).json["lote_id"];process(client,lot)
    def generate(modality):
        with app.app_context():return exportation.export(lot,True,modality,"todos")[1]
    with ThreadPoolExecutor(max_workers=2) as pool:
        counts=list(pool.map(generate,["contado","credito"]))
    assert sorted(counts)==[1,2]
    summary=client.get(f"/api/v1/lotes/{lot}/resumen").json
    assert summary["registros"]["exportados"] in counts
    assert summary["ultima_exportacion"]["cantidad"]==summary["registros"]["exportados"]
