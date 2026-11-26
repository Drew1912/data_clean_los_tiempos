from datetime import date
from uuid import UUID

from .lotes import connection
from ..services.auditing import ACTIONS
from ..services.errors import InputError


def search(page, size, filters):
    clauses, values = [], []
    for key, column in (("accion", "accion"), ("resultado", "resultado"), ("usuario", "usuario_nombre")):
        value = filters.get(key, "")
        if not value:
            continue
        if (key == "accion" and value not in ACTIONS) or (key == "resultado" and value not in {"exito", "rechazado", "error"}) or len(value) > 80:
            raise InputError("FILTRO_INVALIDO", "Filtro de auditoría no admitido")
        clauses.append(column+"=%s"); values.append(value)
    if filters.get("lote_id"):
        try: identifier = UUID(filters["lote_id"])
        except ValueError as error: raise InputError("FILTRO_INVALIDO", "El lote debe ser un UUID válido") from error
        clauses.append("lote_id=%s"); values.append(identifier)
    dates = {}
    for key in ("desde", "hasta"):
        value = filters.get(key, "")
        if value:
            try:
                parsed = date.fromisoformat(value)
                if parsed.isoformat() != value: raise ValueError()
                dates[key] = parsed
            except ValueError as error:
                raise InputError("FECHA_INVALIDA", "Usa fechas válidas AAAA-MM-DD") from error
    if dates.get("desde") and dates.get("hasta") and dates["desde"] > dates["hasta"]:
        raise InputError("RANGO_INVALIDO", "La fecha inicial no puede superar la final")
    if "desde" in dates:
        clauses.append("ocurrido_en >= (%s::date::timestamp AT TIME ZONE 'America/La_Paz')"); values.append(dates["desde"])
    if "hasta" in dates:
        clauses.append("ocurrido_en < ((%s::date + 1)::timestamp AT TIME ZONE 'America/La_Paz')"); values.append(dates["hasta"])
    where = " AND ".join(clauses) or "TRUE"
    with connection() as conn:
        # Conteo y página coherentes aunque se agreguen eventos concurrentemente.
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        total = conn.execute("SELECT COUNT(*) AS n FROM auditoria WHERE "+where, values).fetchone()["n"]
        rows = conn.execute("SELECT * FROM auditoria WHERE "+where+" ORDER BY ocurrido_en DESC,id DESC LIMIT %s OFFSET %s", (*values, size, (page-1)*size)).fetchall()
    return {"datos": [dict(row, id=str(row["id"]), ocurrido_en=row["ocurrido_en"].isoformat(),
                          lote_id=str(row["lote_id"]) if row["lote_id"] else None, descripcion=ACTIONS[row["accion"]]) for row in rows],
            "total": total, "pagina": page, "tamano": size,
            "acciones": [{"codigo": key, "nombre": value} for key, value in ACTIONS.items()]}
