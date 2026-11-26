"""Demostración HTTP reproducible; envía solamente el CSV ficticio del proyecto."""
import argparse
import json
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import Request, build_opener, HTTPCookieProcessor
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    base = args.url.rstrip("/") + "/api/v1"
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    csrf = None
    boundary = "demo_" + uuid4().hex
    sample = (Path(__file__).resolve().parents[1] / "frontend/public/ejemplo_facturas.csv").read_bytes()
    manifest = json.dumps({"archivos": [{"indice": 0, "perfil_id": "demo_cabecera_csv_f1", "perfil_version": "1"}]})
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="manifiesto"\r\n\r\n{manifest}\r\n'
            f'--{boundary}\r\nContent-Disposition: form-data; name="archivos"; filename="ejemplo_facturas.csv"\r\n'
            'Content-Type: text/csv\r\n\r\n').encode() + sample + f'\r\n--{boundary}--\r\n'.encode()

    def call(path, method="GET", data=None, headers=None):
        request_headers = dict(headers or {})
        if method == "POST" and csrf:
            request_headers["X-CSRF-Token"] = csrf
        with opener.open(Request(base + path, data=data, method=method, headers=request_headers), timeout=90) as response:
            return json.load(response)

    csrf = call("/auth/sesion")["csrf_token"]
    csrf = call("/auth/login", "POST", json.dumps({"usuario":"admin", "contrasena":"admin"}).encode(), {"Content-Type":"application/json"})["csrf_token"]
    lot = call("/lotes", "POST", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    assert lot["puede_procesar"]
    lot_id = lot["lote_id"]
    summary = call(f"/lotes/{lot_id}/procesamiento", "POST", b"")
    assert summary["registros"]["cargados"] == 5
    assert summary["registros"]["validos"] == 3
    assert summary["registros"]["observados"] == 2
    records = call(f"/lotes/{lot_id}/registros")
    notes = call(f"/lotes/{lot_id}/observaciones")
    assert records["datos"][0]["numero_factura"] == "000101"
    assert records["datos"][0]["nit_ci"] == "00012345001"
    assert [row["monto_numeral"] for row in records["datos"]] == ["151.89", "333.60", "2680.00"]
    assert notes["total"] == 5
    print("OK HTTP: carga y limpieza; 5 cargados = 3 validos + 2 observados; 5 incidencias.")
    print("Lote ficticio:", lot_id)
    call("/auth/logout", "POST", b"")


if __name__ == "__main__":
    main()
