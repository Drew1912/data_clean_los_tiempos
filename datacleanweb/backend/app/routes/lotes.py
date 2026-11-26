import json

from flask import Blueprint, jsonify, request, Response, g

from ..profiles import list_profiles
from ..repositories import lotes as repository
from ..services import importation
from ..services.errors import InputError

lotes = Blueprint("lotes", __name__)


def query(allowed):
    if set(request.args) - set(allowed) or any(len(request.args.getlist(k)) != 1 for k in request.args):
        raise InputError("PARAMETRO_INVALIDO", "Hay parámetros desconocidos o repetidos")


def pagination():
    try:
        page, size = int(request.args.get("pagina", "1")), int(request.args.get("tamano", "50"))
        if page < 1 or not 1 <= size <= 100 or page > 1000000:
            raise ValueError()
        return page, size
    except ValueError as error:
        raise InputError("PAGINACION_INVALIDA", "Página positiva y tamaño entre 1 y 100") from error


@lotes.get("/perfiles")
def profiles():
    query([])
    return jsonify(datos=list_profiles())


@lotes.post("/lotes")
def upload():
    query([])
    if request.mimetype != "multipart/form-data":
        raise InputError("TIPO_PETICION_INVALIDO", "La carga requiere multipart/form-data", 415)
    if set(request.files) - {"archivos"} or set(request.form) != {"manifiesto"} or len(request.form.getlist("manifiesto")) != 1:
        raise InputError("MANIFIESTO_INVALIDO", "Envía archivos y un único manifiesto")
    try:
        manifest = json.loads(request.form["manifiesto"])
    except ValueError as error:
        raise InputError("MANIFIESTO_INVALIDO", "El manifiesto no es JSON válido") from error
    result = importation.create_upload(request.files.getlist("archivos"), manifest)
    return jsonify(result), 201


@lotes.get("/lotes/<lot_id>")
def describe(lot_id):
    query([])
    return jsonify(repository.describe(lot_id))


@lotes.get('/lotes')
def list_lots():
    query(['pagina', 'tamano'])
    page, size = pagination()
    where, params = ('TRUE', ()) if g.usuario['rol']=='administrador' else ('l.creado_por=%s', (g.usuario['id'],))
    with repository.connection() as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        total = conn.execute('SELECT COUNT(*) AS n FROM lote l WHERE '+where, params).fetchone()['n']
        rows = conn.execute('SELECT l.id,l.estado,l.creado_en,l.vence_en,u.nombre AS usuario,COUNT(a.id) AS archivos '
            'FROM lote l LEFT JOIN usuario u ON u.id=l.creado_por LEFT JOIN archivo a ON a.lote_id=l.id WHERE '+where+
            ' GROUP BY l.id,u.nombre ORDER BY l.creado_en DESC,l.id DESC LIMIT %s OFFSET %s', (*params,size,(page-1)*size)).fetchall()
    return jsonify(datos=[dict(row,id=str(row['id']),creado_en=row['creado_en'].isoformat(),vence_en=row['vence_en'].isoformat()) for row in rows],
                   total=total,pagina=page,tamano=size)


@lotes.post("/lotes/<lot_id>/procesamiento")
def process(lot_id):
    query([])
    classification = None
    if request.get_data():
        if not request.is_json:
            raise InputError("TIPO_PETICION_INVALIDO", "La clasificación requiere JSON", 415)
        classification = request.get_json()
        if not isinstance(classification, dict):
            raise InputError("CLASIFICACION_INVALIDA", "La clasificación debe ser un objeto JSON")
    return jsonify(importation.process(lot_id, classification))


@lotes.get("/lotes/<lot_id>/resumen")
def summary(lot_id):
    query(["modalidad", "departamento"])
    return jsonify(repository.summary(lot_id, request.args.get("modalidad", "todos"), request.args.get("departamento", "todos")))


@lotes.get("/lotes/<lot_id>/registros")
def records(lot_id):
    query(["modalidad", "departamento", "pagina", "tamano", "estado"])
    return jsonify(repository.valid_records(lot_id, *pagination(), request.args.get("modalidad", "todos"), request.args.get("departamento", "todos"), request.args.get("estado", "valido")))


@lotes.get("/lotes/<lot_id>/observaciones")
def observations(lot_id):
    query(["pagina", "tamano"])
    return jsonify(repository.observations(lot_id, *pagination()))


@lotes.get("/lotes/<lot_id>/relaciones")
def relations(lot_id):
    from ..services.matching import find_relations
    query(["pagina", "tamano"])
    page, size = pagination()
    rows = repository.relation_records(lot_id)
    groups, unmatched = find_relations(rows)
    return jsonify(datos=groups[(page - 1) * size:page * size], pagina=page, tamano=size,
                   total=len(groups), sin_relacion=unmatched, registros_evaluados=len(rows))


@lotes.post("/lotes/<lot_id>/comparaciones")
def comparisons(lot_id):
    from ..services.comparison import compare_files
    query([])
    if not request.is_json:
        raise InputError("TIPO_PETICION_INVALIDO", "La comparación requiere JSON", 415)
    files, rows = repository.comparison_context(lot_id)
    result = compare_files(files, rows, request.get_json())
    if result["pagina"] == 1 and result["configuracion"]["filtro"] == "todos":
        from ..services.auditing import record_separately
        record_separately("COMPARACION_EJECUTADA", lot_id=lot_id, details={"archivos":len(result["archivos"]), "registros":len(rows), "configuracion":result["configuracion_id"]})
    return jsonify(result)


@lotes.post("/lotes/<lot_id>/exportaciones/<kind>")
def export(lot_id, kind):
    from ..services import exportation
    query([])
    if kind not in {"limpios", "observaciones"}:
        raise InputError("RECURSO_NO_DISPONIBLE", "Recurso no disponible", 404)
    filters = {}
    if kind == "limpios":
        if not request.is_json:
            raise InputError("TIPO_PETICION_INVALIDO", "La exportación limpia requiere JSON", 415)
        filters = request.get_json()
        if not isinstance(filters, dict) or set(filters) - {"modalidad", "departamento"} or any(not isinstance(v, str) for v in filters.values()):
            raise InputError("FILTRO_INVALIDO", "Envía únicamente modalidad y departamento como texto")
    elif request.get_data():
        raise InputError("CUERPO_NO_ADMITIDO", "El reporte de observaciones no recibe cuerpo ni filtros")
    data, count, identifier = exportation.export(lot_id, kind == "limpios", filters.get("modalidad", "todos"), filters.get("departamento", "todos"))
    name = ("consolidado" if kind == "limpios" else "observaciones") + "_" + identifier + ".xlsx"
    return Response(data, mimetype=exportation.MIME, headers={"Content-Disposition": f'attachment; filename="{name}"',
                    "X-Registros-Exportados" if kind == "limpios" else "X-Observaciones-Exportadas": str(count)})
