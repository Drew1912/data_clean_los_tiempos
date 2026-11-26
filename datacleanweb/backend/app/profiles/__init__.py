from copy import deepcopy
import json
from pathlib import Path

_BASE = json.loads(Path(__file__).with_name("demostracion.json").read_text(encoding="utf-8"))
_MATERIAL = json.loads(Path(__file__).with_name("material.json").read_text(encoding="utf-8"))
_VARIANTS = {
    "demo_cabecera_csv_f1": (".csv", 1, "Demostración CSV · UTF-8 · ; · cabecera fila 1"),
    "demo_cabecera_xlsx_f1": (".xlsx", 1, "Demostración Excel · hoja Facturas · fila 1"),
    "demo_cabecera_xlsx_f4": (".xlsx", 4, "Demostración Excel · hoja Facturas · fila 4"),
}


def get_profile(profile_id, version="1"):
    if version != _BASE["version"]:
        return None
    if profile_id == "auto":
        return {"id": "auto", "version": "1", "descripcion": "Detectar por hojas y cabeceras", "sintetico": False,
                "extensiones": [".xls", ".xlsx", ".csv"], "advertencias": []}
    for source in _MATERIAL:
        if source["id"] == profile_id:
            result = deepcopy(_BASE)
            result.update(deepcopy(source), sintetico=False, version="1", extensiones=[source["extension"]],
                          permitir_cabeceras_vacias=True, evidencia="Estructuras observadas en material; catálogo observado 0C/1C")
            result["alias"].update(source["alias"])  # Restaurar campos canónicos que la fuente no contiene.
            # La configuración específica no hereda alias DEMO que podrían elegir otra columna.
            result["alias"] = {key: source["alias"].get(key, [key.upper()] if key in {"cuf", "anulado"} else []) for key in _BASE["alias"]}
            result["cajas_admitidas"] = {"0C": "cochabamba", "1C": "cochabamba"}
            result["advertencias"] = ["Estructura observada: los campos ausentes no se infieren ni se completan desde el nombre del archivo",
                                       "Los códigos 0C/1C son los observados en las muestras; otros códigos requieren catálogo",
                                       "CUFD y código de autorización se conservan como adicionales, no se equiparan a CUF"]
            return result
    if profile_id not in _VARIANTS:
        return None
    extension, header, description = _VARIANTS[profile_id]
    return dict(deepcopy(_BASE), id=profile_id, extension=extension,
                extensiones=[extension], fila_encabezado=header, descripcion=description)


def list_profiles():
    return [get_profile("auto"), *[get_profile(p["id"]) for p in _MATERIAL], *[get_profile(profile_id) for profile_id in _VARIANTS]]
