# Fase 2.1 — Infraestructura mínima

> Entrega histórica de infraestructura. La carga y limpieza ya se implementan en [Fase 2.2/2.3](../fase_2_2_3/README.md). Sus instrucciones reutilizan esta base; las afirmaciones siguientes sobre rutas de negocio no implementadas describen el estado de Fase 2.1.

Fecha de revisión: 2026-11-17. Fuentes: PROMPT.md, REVISION_TECNICA_FASE_1.md, 12 RF/6 RNF y decisiones del usuario. Arquitectura, contratos y cuatro tablas conservados. Las correcciones críticas/altas se documentan en [C-01 a C-05](../fase_1/05_CORRECCIONES_CRITICAS.md); C-06 se ejecuta aquí por encargo explícito de probar SQL.

## Implementado

- Tres definiciones Compose: Next.js, Flask y PostgreSQL 17, salud y volúmenes. Solo frontend expuesto en 127.0.0.1:3000; backend/DB sin puertos de host.
- Next.js/TypeScript: pantalla de conexión accesible, cliente HTTP y proxy GET `/api/v1/health`, sin caché ni URL de DB en navegador.
- Flask: factory, blueprint de salud y respuesta 200 `{estado:"ok",db:"ok"}` cuando conecta y encuentra las cuatro tablas; fallo controlado 503, sin DSN/credenciales/stack.
- El SQL original de Fase 1 se monta sin duplicarlo como inicialización de PostgreSQL. No se cambiaron tablas, campos ni restricciones. Pruebas ejercitan las estructuras reales.
- Pruebas de salud, SQL y artefactos de revisión, más un smoke HTTP reproducible. Fixtures solo ficticios; dependencias de lectura/BPMN existen en requirements-dev, no en runtime del backend.

No implementados: importación HTTP, clasificación, limpieza, detección de duplicados, consolidación, filtros de facturación, exportación, purga/TTL ni métricas RNF-02. Las rutas de negocio restantes devuelven 404; no hay respuestas de éxito simuladas. No se integra el cruce histórico de scripts/.

## Ejecución recomendada con Docker Compose

Requisito del equipo: Docker Desktop iniciado con motor Linux y Compose v2. No hace falta un proyecto Docker previo; `compose.yaml` crea los servicios/red/volúmenes. Esta instalación no se modificó durante la tarea.

Desde la raíz del proyecto, PowerShell:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
# Editar POSTGRES_PASSWORD en .env: usar una clave local propia.
docker version
docker compose version
docker compose config --quiet
docker compose up --build --wait
docker compose ps
python tools/smoke_connectivity.py
```

Esperado: tres servicios saludables y `OK: pagina HTTP 200 y proxy /api/v1/health HTTP 200`. Abrir `http://127.0.0.1:3000`, pulsar «Comprobar conexión». Si el puerto 3000 está ocupado, cambiar FRONTEND_PORT en .env y pasar `--url http://127.0.0.1:<puerto>` al smoke. La URL del backend queda solo en el proceso Next.js.

Inspección y parada sin borrar volúmenes:

```powershell
docker compose logs --tail 50 backend frontend db
docker compose down
```

El SQL de `/docker-entrypoint-initdb.d/` se ejecuta solo sobre un volumen PostgreSQL nuevo. No volver a aplicar el CREATE TABLE sobre una DB inicializada ni borrar volúmenes para ocultar errores; una modificación futura requiere migración explícita. Este esquema inicial ya se ejecutó en una instancia local aislada, pero no se verificó el entrypoint Docker en este equipo.

Las imágenes usan Python 3.12, Node 22 y PostgreSQL 17. Frontend usa package-lock.json y `npm ci`; dependencias directas Python fijadas en requirements.txt. No hay credenciales reales en el repositorio. Flask usa su servidor de desarrollo sin debugger/reloader: esta entrega sirve para el prototipo local, no para producción.

## Pruebas con Compose disponible

Crear entorno de pruebas local y usar las mismas dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Sin TEST_DATABASE_URL, los tests que requieren PostgreSQL se omiten expresamente. Para ejecutarlos desde un contenedor backend contra una DB dedicada de pruebas, manteniendo DB sin puertos públicos:

```powershell
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" dataclean_pruebas'
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d dataclean_pruebas -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/001_inicial.sql'
docker compose run --rm --no-deps --user root --workdir /workspace/backend -v "${PWD}:/workspace:ro" backend sh -c 'pip install -r /workspace/backend/requirements-dev.txt && TEST_DATABASE_URL="host=db dbname=dataclean_pruebas" PGDATABASE=dataclean_pruebas python -m pytest -c /workspace/pytest.ini /workspace/backend/tests -q -p no:cacheprovider'
```

Inicializar `dataclean_pruebas` una sola vez en ese entorno. La contraseña/usuario se heredan de PGUSER/PGPASSWORD del servicio backend; no incluirlos en comandos ni salidas. Cada prueba SQL crea su propio esquema aleatorio y lo elimina al finalizar. Nunca configurar TEST_DATABASE_URL hacia una base empresarial: las pruebas de este proyecto son exclusivamente sintéticas. Comandos Compose documentados, todavía no ejecutados aquí.

## Alternativa local utilizada en la verificación

Equipo observado: Windows, Node 23.3.0, npm 10.9.0, Python 3.11.9 y PostgreSQL 17 instalado bajo `C:\Program Files\PostgreSQL\17\bin`. Next.js 16.4.6, React 19.3.1, TypeScript 7.0.2, Flask 3.1.3 y psycopg 3.3.9. El build local no acredita las imágenes Linux con Node 22/Python 3.12: su prueba queda pendiente con Docker.

Preparación inicial, solo en un directorio/base de pruebas nuevos:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Push-Location frontend
npm.cmd ci
npm.cmd run build
npm.cmd run typecheck
Pop-Location

$pgBin = 'C:\Program Files\PostgreSQL\17\bin'
New-Item -ItemType Directory -Path .test-data -Force | Out-Null
# Solo primera vez: el cluster y usuario son exclusivamente para fixtures ficticios.
& "$pgBin\initdb.exe" -D .test-data/postgres -U dataclean_test -A trust --encoding=UTF8 --locale=C
& "$pgBin\pg_ctl.exe" -D .test-data/postgres -l .test-data/postgres.log -o '-p 55439 -h 127.0.0.1' -w start
& "$pgBin\createdb.exe" -h 127.0.0.1 -p 55439 -U dataclean_test dataclean_test
& "$pgBin\psql.exe" -h 127.0.0.1 -p 55439 -U dataclean_test -d dataclean_test -v ON_ERROR_STOP=1 -f docs/fase_1/schema_propuesto.sql
```

No repetir initdb/createdb/DDL si ya existen; en otra sesión basta iniciar ese cluster con pg_ctl. Autenticación trust de esta alternativa solo corresponde a una instancia 127.0.0.1 de fixtures; Compose usa contraseña. No modificar servicios PostgreSQL existentes.

Terminal 1, desde backend/:

```powershell
$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
..\.venv\Scripts\python.exe -m flask --app app:create_app run --host=127.0.0.1 --port=8000 --no-debugger --no-reload
```

Terminal 2, desde frontend/:

```powershell
$env:BACKEND_URL='http://127.0.0.1:8000'
$env:PORT='3000'
npm.cmd run start
```

`npm start` prepara los estáticos y arranca el servidor standalone en 127.0.0.1. Docker copia esos estáticos en build y usa directamente server.js con su hostname interno; no ejecuta el helper local.

Terminal 3, raíz:

```powershell
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/smoke_connectivity.py
```

Escenario de caída/recuperación, manteniendo frontend y backend encendidos:

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' -D .test-data/postgres -w -m fast stop
.\.venv\Scripts\python.exe tools/smoke_connectivity.py --expect-status 503
& 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' -D .test-data/postgres -l .test-data/postgres.log -o '-p 55439 -h 127.0.0.1' -w start
.\.venv\Scripts\python.exe tools/smoke_connectivity.py
```

Cerrar con Ctrl+C los dos servidores y parar ese cluster con pg_ctl; conservar el directorio de prueba para no eliminar evidencia. No se dejan servidores propios de la verificación activos al cerrar esta tarea.

## Resultados realmente ejecutados

| Verificación | Resultado observado |
|---|---|
| DDL completo original | COMMIT correcto en PostgreSQL 17 aislado; cuatro tablas y seis índices explícitos creados |
| pytest con TEST_DATABASE_URL | **23 passed**, sin omisiones, en 10,80 s en la ejecución registrada |
| Restricciones PostgreSQL | Obligatorios/valores permitidos, código/modalidad coherentes, fila positiva, FK compuesta observación, origen único CSV con hoja NULL, hojas distintas y cascadas comprobadas |
| Integridad/consultas | Ceros y Decimal exacto preservados; misma factura en fuentes diferentes admitida sin deduplicación; filtros AND y exclusión de estado observado comprobados a nivel SQL |
| Salud | PostgreSQL real 200; conexión inválida y esquema incompleto 503 sin secretos; ruta de facturación no implementada 404 |
| Perfiles C-01 | CSV y Excel sintéticos con cabecera 1/4, ceros/columnas complementarias y DD/MM/AAAA leídos; no perfiles empresariales validados |
| BPMN C-05 | XSD oficial OMG válido, IDs/referencias/carriles, caminos a fin y DI comprobados; no prueba GUI Camunda ni motor |
| Frontend | Build Next.js y tsc correctos |
| HTTP integrado | Página 200 y Next.js→Flask→PostgreSQL 200; caída DB→503 controlado; recuperación→200 |
| Compose | YAML leído y estructura de tres servicios/puertos/dependencias revisada; **no ejecutado docker compose config/build/up**, Docker no disponible |
| Pruebas de producto T01–T12/N01–N06 completas | No ejecutadas: facturación, rendimiento, usabilidad y protección integral todavía pendientes |

El smoke HTTP no equivale a una prueba visual o clic automatizado de navegador. Las consultas SQL de filtros no acreditan RF-05/06 de extremo a extremo: sus endpoints aún no están implementados.

## Criterio de cierre y pendientes

Infraestructura preparada, esquema ejecutado y comunicación local comprobada. El pase de contenedores queda pendiente hasta disponer de Docker Desktop/motor Linux. No se declara Fase 2.1 totalmente verificada en Docker ni ningún RF de facturación terminado.

Para datos reales todavía faltan muestra principal Excel/CSV anonimizada, hoja/fila/convenios confirmados, catálogo de CAJA y decisión de Contabilidad sobre avisos de duplicidad. Seguir con procesamiento de facturación requerirá otra etapa; esta entrega se detiene aquí.

Referencias técnicas consultadas: [instalación Next.js](https://nextjs.org/docs/app/getting-started/installation), [dependencias y salud Compose](https://docs.docker.com/compose/how-tos/startup-order/), [despliegue Flask](https://flask.palletsprojects.com/en/stable/tutorial/deploy/) y [BPMN 2.0 OMG](https://www.omg.org/spec/BPMN/2.0/).
