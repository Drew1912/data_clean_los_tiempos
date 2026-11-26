import hashlib
from pathlib import Path
import re
from uuid import uuid4

from flask import current_app

from ..profiles import get_profile, list_profiles
from ..readers.invoices import read_invoice, MAX_ROWS
from ..repositories import lotes
from .cleaning import clean_record, mark_exact_repetitions
from .errors import InputError, FileError


def private_path(name):
    if not re.fullmatch(r"[0-9a-f]{32}\.bin", name):
        raise InputError("ORIGINAL_NO_DISPONIBLE", "Referencia de archivo no válida", 500)
    root = Path(current_app.config["UPLOAD_ROOT"]).resolve()
    target = (root / name).resolve()
    if target.parent != root:
        raise InputError("ORIGINAL_NO_DISPONIBLE", "Referencia de archivo no válida", 500)
    return target


def create_upload(uploads, manifest):
    if not isinstance(manifest, dict) or set(manifest) != {"archivos"} or not isinstance(manifest["archivos"], list):
        raise InputError("MANIFIESTO_INVALIDO", "El manifiesto debe contener una lista de archivos")
    definitions = manifest["archivos"]
    if not uploads or len(uploads) != len(definitions):
        raise InputError("MANIFIESTO_INVALIDO", "Cada archivo necesita un perfil en el manifiesto")
    if len(uploads) > 10:
        raise InputError("LIMITE_ARCHIVOS", "Admite como máximo 10 archivos por lote", 413)
    by_index = {}
    for definition in definitions:
        if not isinstance(definition, dict) or set(definition) != {"indice", "perfil_id", "perfil_version"}:
            raise InputError("MANIFIESTO_INVALIDO", "Cada entrada necesita índice, perfil y versión")
        index = definition["indice"]
        if (type(index) is not int or index < 0 or index >= len(uploads) or index in by_index
                or not isinstance(definition["perfil_id"], str) or not isinstance(definition["perfil_version"], str)):
            raise InputError("MANIFIESTO_INVALIDO", "Los índices deben ser únicos y los perfiles/versiones deben ser texto")
        by_index[index] = definition
    files, issues, contents = [], [], []
    total_bytes, total_rows = 0, 0
    for index, upload in enumerate(uploads):
        data = upload.stream.read(current_app.config["MAX_FILE_BYTES"] + 1)
        total_bytes += len(data)
        if len(data) > current_app.config["MAX_FILE_BYTES"] or total_bytes > current_app.config["MAX_BATCH_BYTES"]:
            raise InputError("LIMITE_TAMANO", "Máximo 10 MiB por archivo y 25 MiB por lote", 413)
        definition = by_index[index]
        profile = get_profile(definition["perfil_id"], definition["perfil_version"])
        name = upload.filename or "sin_nombre"
        safe_name = Path(name.replace("\\", "/")).name[:200]
        extension = Path(safe_name).suffix.lower()
        file_id = uuid4()
        metadata = {"id": file_id, "posicion": index, "nombre_original": safe_name,
                    "nombre_interno": file_id.hex + ".bin", "extension": extension,
                    "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                    "perfil_id": definition["perfil_id"], "perfil_version": definition["perfil_version"],
                    "perfil_snapshot": profile, "estado": "rechazado", "hojas": []}
        try:
            if not upload.filename or any(c in name for c in ("/", "\\", "\x00")) or any(ord(c) < 32 for c in name):
                raise FileError("NOMBRE_INVALIDO", "Nombre de archivo vacío o con caracteres/rutas no admitidos")
            if extension not in {".xls", ".xlsx", ".csv"}:
                raise FileError("EXTENSION_NO_ADMITIDA", "Se admiten .xls, .xlsx y .csv")
            if not profile:
                raise FileError("PERFIL_DESCONOCIDO", "El perfil o su versión no están habilitados")
            if profile["id"] == "auto":
                matches = []
                for candidate in list_profiles():
                    if candidate["id"] == "auto" or candidate["extension"] != extension:
                        continue
                    try:
                        parsed = read_invoice(data, candidate)
                        matches.append((candidate, parsed))
                    except FileError:
                        pass
                if not matches:
                    raise FileError("FORMATO_DESCONOCIDO", "No se reconocieron las hojas y cabeceras del archivo en los perfiles disponibles. Revisa el formato de lectura; elegir un perfil incompatible no lo corrige")
                if len(matches) > 1:
                    raise FileError("FORMATO_AMBIGUO", "Hay varios perfiles compatibles. Selecciona el perfil de lectura explícitamente")
                profile, parsed = matches[0]
                metadata.update(perfil_id=profile["id"], perfil_version=profile["version"], perfil_snapshot=profile)
            else:
                parsed = None
            if profile["extension"] != extension:
                raise FileError("PERFIL_INCOMPATIBLE", "El formato de archivo no corresponde al perfil elegido")
            records, sheets, sheet_issues = parsed if parsed is not None else read_invoice(data, profile)
            total_rows += len(records)
            if total_rows > MAX_ROWS:
                raise InputError("LIMITE_FILAS", "El lote supera 5.000 filas de datos", 413)
            metadata.update(estado="admitido", hojas=sheets)
            issues.extend(dict(note, archivo_id=file_id) for note in sheet_issues)
            contents.append((metadata["nombre_interno"], data))
        except FileError as error:
            issues.append({"archivo_id": file_id, "tipo": error.code, "motivo": error.message})
        files.append(metadata)
    lot_id, written = uuid4(), []
    try:
        for name, content in contents:
            path = private_path(name)
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with path.open("xb") as handle:
                written.append(path)
                handle.write(content)
        lotes.create_lot(lot_id, files, issues)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return lotes.describe(lot_id)


def process(lot_id, classification=None):
    files = lotes.claim_processing(lot_id, classification)
    if files is None:
        return lotes.summary(lot_id)
    try:
        rows, issues = [], []
        for file in files:
            if file["estado"] != "admitido":
                continue
            with private_path(file["nombre_interno"]).open("rb") as handle:
                data = handle.read(current_app.config["MAX_FILE_BYTES"] + 1)
            if len(data) != file["bytes"] or hashlib.sha256(data).hexdigest() != file["sha256"]:
                raise InputError("ORIGINAL_ALTERADO", "Cambió un original guardado; realiza una nueva carga", 409)
            source_rows, _, _ = read_invoice(data, file["perfil_snapshot"])
            for source in source_rows:
                row, row_issues = clean_record(source, file["id"], file["perfil_snapshot"])
                rows.append(row)
                issues.extend(row_issues)
        issues.extend(mark_exact_repetitions(rows))
        lotes.complete(lot_id, rows, issues)
    except Exception:
        lotes.mark_failed(lot_id)
        raise
    return lotes.summary(lot_id)


def cleanup_expired():
    """Limpieza explícita; solo archivos UUID de lotes vencidos no procesándose."""
    count = 0
    from .auditing import record
    with lotes.connection() as conn:
        expired = conn.execute("SELECT id FROM lote WHERE vence_en <= CURRENT_TIMESTAMP AND estado <> 'procesando' FOR UPDATE").fetchall()
        for lot in expired:
            for file in lotes.files_for_lot(lot["id"], conn):
                private_path(file["nombre_interno"]).unlink(missing_ok=True)
            conn.execute("DELETE FROM lote WHERE id=%s", (lot["id"],))
            record(conn, "LOTE_ELIMINADO", lot_id=lot["id"])
            count += 1
    return count
