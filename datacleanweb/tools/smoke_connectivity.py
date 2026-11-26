"""Prueba HTTP de página y proxy Next.js -> Flask -> PostgreSQL, sin datos administrativos."""
import argparse
import json
import re
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3000")
    parser.add_argument("--expect-status", type=int, default=200, choices=[200, 503])
    args = parser.parse_args()
    with urllib.request.urlopen(args.url, timeout=10) as response:
        assert response.status == 200
        page = response.read().decode("utf-8")
        assert "DataClean" in page
    # Comprobar que el servidor standalone entrega los recursos de la pantalla.
    assets = set(re.findall(r'(?:src|href)="(/_next/static/[^"?]+)', page))
    assert assets, "La pagina no referencia recursos estaticos"
    for asset in assets:
        with urllib.request.urlopen(args.url.rstrip("/") + asset, timeout=10) as response:
            assert response.status == 200
    request = urllib.request.Request(args.url.rstrip("/") + "/api/v1/health")
    try:
        response = urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        assert response.status == args.expect_status, response.status
        body = json.load(response)
        expected = {"estado": "ok", "db": "ok"} if args.expect_status == 200 else {"estado": "error", "db": "no_disponible"}
        assert body == expected, body
        assert response.headers["Cache-Control"] == "no-store"
    print(f"OK: pagina HTTP 200 y proxy /api/v1/health HTTP {args.expect_status}")


if __name__ == "__main__":
    main()
