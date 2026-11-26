import os
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.types.json import Jsonb

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Requiere PostgreSQL de prueba explícito")
DDL = Path(__file__).resolve().parents[2] / "docs/fase_1/schema_propuesto.sql"


@pytest.fixture
def db():
    # Solo un esquema aleatorio nuevo; nunca tablas del esquema público del usuario.
    schema = "test_" + uuid4().hex
    with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            ddl = DDL.read_text(encoding="utf-8").replace("BEGIN;", "").replace("COMMIT;", "")
            conn.execute(ddl)
            yield conn
        finally:
            conn.execute("SET search_path TO public")
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def seed(conn):
    lote, a, b = uuid4(), uuid4(), uuid4()
    conn.execute("INSERT INTO lote(id,vence_en) VALUES (%s,CURRENT_TIMESTAMP + INTERVAL '1 day')", (lote,))
    for position, archivo in enumerate((a, b)):
        conn.execute(
            "INSERT INTO archivo(id,lote_id,posicion,nombre_original,nombre_interno,extension,bytes,sha256,"
            "perfil_id,perfil_version,perfil_snapshot,estado) VALUES (%s,%s,%s,'demo.csv',%s,'.csv',100,%s,'demo','1','{}','admitido')",
            (archivo, lote, position, str(archivo), "a" * 64),
        )
    return lote, a, b


def record(conn, archivo, **overrides):
    fields = dict(id=uuid4(), archivo_id=archivo, hoja=None, fila=2, original=Jsonb({"NRO FACTURA": "000101"}),
                  numero_factura="000101", fecha_factura="2026-10-17", nit_ci="00012345001",
                  modalidad_codigo="C", caja_codigo="0C", monto_numeral=Decimal("2680.00"),
                  modalidad="contado", departamento="cochabamba", estado="valido")
    fields.update(overrides)
    statement = sql.SQL("INSERT INTO registro ({}) VALUES ({})").format(
        sql.SQL(",").join(map(sql.Identifier, fields)),
        sql.SQL(",").join(sql.Placeholder() for _ in fields),
    )
    conn.execute(statement, list(fields.values()))
    return fields["id"]


def test_exact_values_and_same_invoice_in_different_origins(db):
    _, a, b = seed(db)
    record(db, a)
    record(db, b)
    values = db.execute("SELECT numero_factura,nit_ci,monto_numeral FROM registro").fetchall()
    assert values == [("000101", "00012345001", Decimal("2680.00"))] * 2


@pytest.mark.parametrize("change", [
    {"numero_factura": None}, {"nit_ci": ""}, {"modalidad_codigo": "X"},
    {"modalidad": "credito"}, {"departamento": "desconocido"}, {"fila": 0},
    {"estado": "inventado"}, {"monto_numeral": None},
])
def test_required_fields_and_catalog_constraints(db, change):
    _, a, _ = seed(db)
    with pytest.raises(psycopg.errors.CheckViolation):
        record(db, a, **change)


def test_csv_origin_unique_even_with_null_sheet(db):
    _, a, _ = seed(db)
    record(db, a)
    with pytest.raises(psycopg.errors.UniqueViolation): record(db, a)
    record(db, a, hoja="Facturas", fila=2)
    record(db, a, hoja="Otra", fila=2)


def test_observation_composite_foreign_key(db):
    _, a, b = seed(db)
    registro = record(db, a)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.execute("INSERT INTO observacion(archivo_id,registro_id,fila,tipo,motivo) VALUES (%s,%s,2,'AVISO_POSIBLE_DUPLICADO','demo')", (b, registro))
    db.execute("INSERT INTO observacion(archivo_id,registro_id,fila,tipo,motivo) VALUES (%s,%s,2,'AVISO_POSIBLE_DUPLICADO','demo')", (a, registro))
    # Un aviso no obliga a cambiar estado ni requiere columnas/tablas nuevas.
    assert db.execute("SELECT estado FROM registro WHERE id=%s", (registro,)).fetchone()[0] == "valido"


def test_filters_use_and_and_only_valid_rows(db):
    _, a, _ = seed(db)
    target = record(db, a)
    record(db, a, fila=3, modalidad="credito", modalidad_codigo="P")
    record(db, a, fila=4, departamento="la_paz", caja_codigo="1L")
    record(db, a, fila=5, estado="observado")
    assert db.execute("SELECT id FROM registro WHERE estado='valido' AND modalidad=%s AND departamento=%s", ("contado", "cochabamba")).fetchall() == [(target,)]


def test_cascade_deletes_only_test_lot(db):
    lote, a, _ = seed(db)
    registro = record(db, a)
    db.execute("INSERT INTO observacion(archivo_id,registro_id,fila,tipo,motivo) VALUES (%s,%s,2,'AVISO_DUPLICADO_EXACTO','demo')", (a, registro))
    db.execute("DELETE FROM lote WHERE id=%s", (lote,))
    for table in ("lote", "archivo", "registro", "observacion"):
        assert db.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()[0] == 0
