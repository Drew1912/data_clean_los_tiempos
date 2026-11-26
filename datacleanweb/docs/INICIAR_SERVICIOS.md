# Cómo iniciar los servicios, uno por uno

> **2026-11-24, usuarios y roles:** [Entrega vigente](USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **Actualización 2026-11-24:** [Auditoría implementada](AUDITORIA.md): historial persistente de accesos y operaciones, permiso de consulta comprobado en Flask y nueva página en el menú. Migración 005; el modelo vigente tiene 6 tablas y 68 atributos. Las referencias anteriores a ausencia de historial o cinco tablas describen entregas previas.


> **Entrega anterior de navegación:** Importación, Comparación y Revisión tienen páginas propias y un menú lateral. Para activar esta actualización, detén **solo el frontend** con Ctrl+C en su terminal, entra en `frontend`, ejecuta `npm.cmd run build` y después `npm.cmd run start`. Abre `http://127.0.0.1:3000` y recarga la página. La entrega de auditoría posterior sí requiere migración 005 y reinicio de Flask. [Guía de navegación](MANUAL_USUARIO.md#navegación-por-páginas).

> **Modalidad por contrato — 2026-11-23:** elige columna de contrato por archivo (P = Crédito; C = Contado), antes de limpiar/comparar. Departamento queda fuera del flujo. La migración 004 ya está aplicada en este equipo; en otra copia ejecuta `actualizar-esquema` desde backend. Reinicia Flask, recompila/reinicia Next.js y realiza **Nueva carga**. [Regla, comandos y cambio de alcance](MODALIDAD_CONTRATO.md).

> **Filtros y descargas — 2026-11-23:** reinicia Flask y recompila/reinicia Next.js para habilitar modalidad/departamento y **Descargar Excel limpio / Descargar observaciones**. No requiere migración SQL. [Funcionamiento y pruebas](EXPORTACIONES.md).

> **Login nuevo:** la aplicación ahora requiere **admin / admin**. En una copia anterior, con PostgreSQL iniciado, ejecuta `actualizar-esquema` e `inicializar-admin` desde backend antes de iniciar Flask; después recompila y reinicia Next.js. [Bloques completos para copiar y pegar](LOGIN_ADMIN.md). En este equipo la migración y la cuenta ya se prepararon. Al abrir la página verás el acceso antes de cargar archivos.

> **Excel de `7MO_SEMESTRE/contado o credito`:** ya tienen perfiles de lectura. Para este ajuste basta reiniciar **Flask**, recargar la página y pulsar **Nueva carga**; conserva «Detectar por hojas y cabeceras». No requiere migración ni recompilar Next.js. [Archivos, hojas y limitaciones verificadas](FORMATOS_FEBRERO.md).

> **Actualización para la comparación configurable:** conserva el mismo PostgreSQL y esquema; reinicia Flask para cargar el endpoint nuevo. En la terminal de Next.js, detén el servidor con Ctrl+C, ejecuta `npm.cmd run build` y después `npm.cmd run start`. En el navegador, recarga la página y crea una carga nueva. [Pasos para comparar por factura, NIT/CI y monto](COMPARACION_FACTURAS.md). El botón de limpieza ahora se llama «Limpiar y revisar registros»; para comparar basta cargar, seleccionar columnas y pulsar «Buscar facturas y comparar».

Guía para este equipo Windows, usando PowerShell y el entorno local que ya está preparado. No requiere Docker. La base de pruebas, las tablas, .venv y el frontend compilado ya existen.

Orden: **PostgreSQL → Flask → Next.js → navegador**. Abre tres terminales PowerShell en VS Code. Cada bloque incluye su ruta completa para que puedas copiarlo independientemente de la carpeta en que estés.

## 1. Terminal 1: iniciar PostgreSQL

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb'

& 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' -D '.test-data\postgres' status

if ($LASTEXITCODE -ne 0) {
    & 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' -D '.test-data\postgres' -l '.test-data\postgres.log' -o '-p 55439 -h 127.0.0.1' -w start
}
```

Esperado: `server started` o un mensaje que indique que el servidor ya está ejecutándose. Esta terminal queda libre porque PostgreSQL continúa en segundo plano.

Se utiliza la instancia aislada del proyecto en **127.0.0.1:55439**, base `dataclean_test`. No necesitas ejecutar de nuevo initdb, createdb ni el esquema SQL.

### Si actualizaste el proyecto para admitir los Excel .xls

En este equipo ya se instalaron las dependencias y se aplicó la migración. En otra copia anterior, con PostgreSQL iniciado, ejecuta una vez antes de iniciar Flask:

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb'
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
Set-Location backend
..\.venv\Scripts\python.exe -m flask --app app:create_app actualizar-esquema
```

La migración admite .xls sin borrar datos. Los bloques siguientes incluyen su propia ruta completa. Para tus documentos, consulta [formatos de material y correspondencias](FORMATOS_MATERIAL.md).

## 2. Terminal 2: iniciar el backend Flask

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb\backend'

$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'

..\.venv\Scripts\python.exe -m flask --app app:create_app actualizar-esquema
..\.venv\Scripts\python.exe -m flask --app app:create_app inicializar-admin

..\.venv\Scripts\python.exe -m flask --app app:create_app run --host=127.0.0.1 --port=8000 --no-debugger --no-reload
```

Esperado: `Running on http://127.0.0.1:8000`. **Deja esta terminal abierta.**

Para comprobar el backend, abre http://127.0.0.1:8000/api/v1/health. Debe responder:

```json
{"estado":"ok","db":"ok"}
```

## 3. Terminal 3: iniciar el frontend Next.js

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb\frontend'

$env:BACKEND_URL='http://127.0.0.1:8000'
$env:PORT='3000'

npm.cmd run start
```

Esperado: `Ready` y la dirección `http://127.0.0.1:3000`. **Deja esta terminal abierta.**

## 4. Abrir y probar la aplicación

Abre **http://127.0.0.1:3000** en tu navegador.

1. Pulsa **Comprobar conexión**.
2. Descarga **CSV de ejemplo** desde la pantalla.
3. Pulsa **Seleccionar archivos** y elige el CSV descargado.
4. Conserva el perfil **Demostración CSV**.
5. Pulsa **1. Cargar archivos** y después **Limpiar y revisar registros**.
6. Revisa **Registros leídos** y **Observaciones**. Para comparar, carga dos o más archivos y sigue [la guía de comparación por columnas](COMPARACION_FACTURAS.md).

Resultado esperado del ejemplo: **5 cargados, 3 válidos, 2 observados y 5 incidencias**. Para probar Excel, descarga su ejemplo y elige el perfil de fila 1 o fila 4 que corresponda.

## 5. Opcional: pruebas desde una cuarta terminal

Con los tres servicios iniciados:

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb'

.\.venv\Scripts\python.exe tools/smoke_connectivity.py
.\.venv\Scripts\python.exe tools/smoke_upload_cleaning.py
```

El primer comando verifica la conexión completa. El segundo crea un lote con el CSV ficticio y comprueba carga, limpieza y cantidades.

Para ejecutar los tests automatizados:

```powershell
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
.\.venv\Scripts\python.exe -m pytest -q
```

## 6. Cómo detener todo

1. En la terminal de **Next.js**, pulsa `Ctrl+C`. Si pregunta si deseas terminar el trabajo por lotes, confirma.
2. En la terminal de **Flask**, pulsa `Ctrl+C`.
3. En la terminal de PostgreSQL, ejecuta:

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb'

& 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' -D '.test-data\postgres' -w -m fast stop
```

Esto detiene los servicios y conserva la base, las tablas y los archivos.

## Si falta una dependencia o cambiaste el código

No necesitas ejecutar esta preparación cada vez que arrancas. Úsala después de actualizar dependencias o para regenerar la versión compilada del frontend. Detén Next.js antes de compilar.

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb'

.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Set-Location frontend
npm.cmd ci
npm.cmd run build
```

Después vuelve a iniciar Flask y Next.js con sus respectivos bloques. Flask está configurado sin recarga automática: los cambios Python requieren reiniciar el backend; los cambios frontend requieren compilar y reiniciar `npm start`.

## Problemas frecuentes

| Mensaje o situación | Qué hacer |
|---|---|
| `Connection refused` o estado de salud 503 | Verifica que PostgreSQL esté iniciado y que DATABASE_URL se haya definido en la misma terminal donde ejecutas Flask |
| Puerto 8000 o 3000 ocupado | Comprueba si ya tienes ese servicio abierto en otra terminal; reutilízalo o detenlo allí con Ctrl+C antes de volver a iniciarlo |
| No existe una versión compilada de Next.js | Ejecuta `npm.cmd run build` dentro de frontend/ y luego `npm.cmd run start` |
| La interfaz no muestra tus últimos cambios | Detén Next.js, vuelve a compilar y reinícialo; para cambios Python reinicia Flask |
| No reconoce perfiles o no conecta con la API | Verifica el backend en /api/v1/health y que BACKEND_URL esté definido antes de iniciar Next.js |
| `ModuleNotFoundError` | Instala requirements-dev.txt usando el Python de .venv, como se indica arriba |

Estas instrucciones reutilizan el entorno ya inicializado de este proyecto. Para otra computadora, consultar la [preparación inicial de infraestructura](fase_2_1/README.md). El [entregable de carga y limpieza](fase_2_2_3/README.md) detalla los perfiles de demostración y sus límites.
