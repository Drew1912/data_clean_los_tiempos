"""Correspondencias explicables; no concilia, agrega, completa ni fusiona filas."""
from collections import defaultdict
from decimal import Decimal
import hashlib
import re


def invoice_key(value):
    if not value:
        return None
    # Solo clave de comparación; el identificador original nunca cambia.
    return value.lstrip("0") or "0" if re.fullmatch(r"[0-9]+", value) else value


def find_relations(rows):
    heads, details = defaultdict(list), defaultdict(list)
    head_by_invoice_box = defaultdict(list)
    for row in rows:
        key = invoice_key(row.get("numero_factura"))
        if key is None:
            continue
        if row.get("nivel_registro") == "detalle":
            if row.get("caja_codigo"):
                details[(key, row["caja_codigo"])].append(row)
        else:
            if row.get("fecha_factura") and row.get("nit_ci"):
                heads[(key, row["fecha_factura"], row["nit_ci"])].append(row)
            if row.get("caja_codigo"):
                head_by_invoice_box[(key, row["caja_codigo"])].append(row)
    result, related = [], set()

    def add(kind, candidates, rule, ambiguous=False):
        candidates = list({row["id"]: row for row in candidates}.values())
        if len({row["origen"]["archivo_id"] for row in candidates}) < 2:
            return
        different = []
        for field in ("monto_numeral", "razon_social", "modalidad_codigo", "cuf", "anulado"):
            comparable = [row[field] for row in candidates if row.get(field) is not None and row.get("nivel_registro") != "detalle"]
            values = {Decimal(value) if field == "monto_numeral" else value for value in comparable}
            if len(values) > 1:
                different.append(field)
        raw_numbers = list(dict.fromkeys(row["numero_factura"] for row in candidates))
        note = "Vínculo propuesto: no completa, elimina ni suma registros"
        if len(raw_numbers) > 1:
            note += "; números equivalentes al comparar ceros iniciales, originales conservados"
        if kind == "cabecera_detalle":
            note += "; el detalle no aporta fecha/NIT para confirmar identidad global"
        ident = hashlib.sha256((kind + "|" + "|".join(sorted(row["id"] for row in candidates))).encode()).hexdigest()[:20]
        result.append({"id": ident, "tipo": kind, "estado": "ambiguo" if ambiguous else "con_diferencias" if different else "candidato",
                       "regla": rule, "facturas_originales": raw_numbers, "campos_diferentes": different,
                       "motivo": note, "registros": candidates})
        related.update(row["id"] for row in candidates)

    for bucket in heads.values():
        boxes = {row["caja_codigo"] for row in bucket if row.get("caja_codigo")}
        for box in sorted(boxes) if boxes else [None]:
            compatible = [row for row in bucket if not row.get("caja_codigo") or row["caja_codigo"] == box]
            add("entre_cabeceras", compatible, "Número de factura + fecha + NIT/CI; cajas conocidas compatibles",
                ambiguous=len(boxes) > 1 and any(not row.get("caja_codigo") for row in compatible))
    for key, lines in details.items():
        candidates = head_by_invoice_box.get(key, [])
        if candidates:
            add("cabecera_detalle", [*candidates, *lines], "Número de factura + CAJA; sin agregar importes de líneas", ambiguous=len(candidates) > 1)
    return result, len(rows) - len(related)
