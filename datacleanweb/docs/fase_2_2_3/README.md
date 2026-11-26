# Entregable: carga y limpieza de facturas

> Actualización de formatos reales: [los cinco Excel de material, soporte .xls y correspondencias](../FORMATOS_MATERIAL.md). Sustituye el límite inicial de solo perfiles DEMO y añade una vista de todos los registros, manteniendo separados los detalles y los campos faltantes.

Para arrancar el proyecto, usa la [guía de inicio de servicios, uno por uno](../INICIAR_SERVICIOS.md).

Fecha: 2026-11-18. Etapa: Fase 2.2/2.3 autorizada por el usuario, reutilizando la base de scripts/. Objetivo: cargar cabeceras Excel/CSV, limpiar formatos seguros y revisar resultados/observaciones sin perder filas ni origen. Se conservan Next.js + Flask + PostgreSQL, cuatro tablas y los endpoints diseñados. No se reactiva la conciliación histórica.

Fuentes: [PROMPT.md](../../PROMPT.md), [RF/RNF](../REQUSITOS.md), [línea base](../LINEA_BASE_MVP.md), [decisiones](../DECISIONES_PENDIENTES.md), [revisión crítica](../fase_1/05_CORRECCIONES_CRITICAS.md), [API](../fase_1/03_API.md), scripts/core_processor.py y scripts/app.py. No se modificaron originales ni requisitos aprobados.

## Qué se puede probar

1. Descargar desde la pantalla un CSV o Excel ficticio (cabecera fila 1 o 4).
2. Elegir uno o varios archivos, hasta diez; indicar el perfil de cada uno.
3. Cargar y ver admisiones/rechazos por archivo. Libros Excel requieren hoja Facturas; Detalle/Productos se reconocen como estructuras separadas y se excluyen con motivo.
4. Pulsar «Limpiar y validar». Se normalizan fechas, importes, identificadores y texto, conservando originales y columnas adicionales.
5. Consultar cabeceras válidas, cambios aplicados y observaciones con contexto original/normalizado, archivo, hoja y fila. Ambas tablas están paginadas.

Ejemplo incluido: **5 cargados = 3 válidos + 2 observados**, con **5 incidencias**. Una fila vacía interior cuenta como observada; la otra tiene fecha imposible, importe ambiguo, modalidad X y caja 9C. Una fila con cuatro errores cuenta una sola vez como observada.

No se implementan todavía descarga de Excel/reportes, edición de facturas, validación tributaria CUF, interpretación de ANULADO, integración cabecera-detalle ni candidatos empresariales por identidad. Los perfiles reales de referencia de docs/fase_1/perfiles/ permanecen deshabilitados: esta entrega usa perfiles DEMO explícitos, no los convierte en reglas empresariales confirmadas.

## Reutilización del algoritmo anterior

No se importa ni ejecuta DataProcessor: su método process_files exige Ventas/Contabilidad y hace un outer join fuera del alcance. La reutilización es una adaptación de etapas, no un wrapper del motor antiguo ni una copia de resultados.

| Parte de scripts/ | Adaptación aplicada | Motivo |
|---|---|---|
| load_data y selección por extensión | Readers CSV/Excel separados y perfiles explícitos | Solo .csv/.xlsx; sin inferir columnas o identificadores con Pandas |
| strip de nombres/textos en clean_data | Recorte seguro de encabezados para alias explícitos, identificadores y normalización de espacios en razón social | Conservar nombre/valor original y registrar cambios; no buscar cualquier columna que contenga MONTO/TOTAL |
| Conversión de fechas con errors=coerce | Fechas por formatos declarados; inválidos conservados con observaciones | No convertir silenciosamente a nulo y luego borrar la fila |
| Sustituir coma por punto, to_numeric y round(2) | Decimal exacto con gramáticas explícitas, sin redondeo automático | 151.89, 333,60 y 2.680,00 admitidos; 1,234 observado, no adivinado |
| dropna de registros incompletos | Persistir toda cabecera leída y observaciones, estados disjuntos | Evitar pérdida de filas y mantener contadores comprobables |
| astype(str) y eliminación de .0 | Texto desde lectura; ceros conservados, formato Excel de ceros explícito respetado | No eliminar contenido de identificadores ni reconstruir precisión perdida |
| pd.merge por NIT+fecha+monto | No reutilizado | Conciliación histórica fuera del MVP |
| Reporte único de cruce | Revisión de limpieza y observaciones en pantalla | Exportación se reserva para otra iteración |

Pandas sigue previsto para consolidación posterior; esta entrega no necesita incorporarlo para leer/limpiar de forma exacta. openpyxl, ya usado en pruebas, pasa a dependencia runtime fijada en 3.1.5. No se añadieron bibliotecas fuera del stack previsto.

## Reglas implementadas y límites

- Alias por perfil, sin coincidencia difusa. Encabezados vacíos, repetidos, colisiones de alias y campos obligatorios ausentes rechazan la fuente explícitamente. Excel no busca arbitrariamente la fila del encabezado.
- Identificadores de texto conservan ceros y complementos CI; solo se recortan extremos. Números Excel se leen desde el XML original, sin pasar por float; identificadores numéricos fraccionarios/científicos o de más de 15 dígitos quedan observados. Un formato explícito como 000000 permite conservar la representación con ceros; no se rellenan por suposición.
- Montos XML usan el literal decimal original, no la representación float de openpyxl. Perfil DEMO: mínimo 0 y máximo dos decimales, sin redondear; reglas reales siguen pendientes. No convertir monedas ni sumar importes.
- Fechas del perfil: DD/MM/AAAA o ISO; las celdas Excel de fecha también se normalizan. Fechas imposibles, hora no autorizada y serial ficticio 1900-02-29 se observan. No hay exclusión temporal por periodo.
- Para cumplir el estado válido del esquema, se incluye clasificación mínima estricta: C/P y patrón más catálogo DEMO 0C/1C/1L/1S. 9C no es válido aunque coincida el patrón; no se clasifica por nombre del archivo. Esto no aprueba un catálogo empresarial ni cierra las reglas de Fase 2.4.
- CUF y ANULADO se conservan sin afirmar validez tributaria. ANULADO no cambia elegibilidad; puede contener texto, booleano o código sin interpretación. Fórmulas en campos obligatorios no se evalúan y producen observación; valores complementarios no interpretables se conservan con aviso no bloqueante cuando corresponde.
- Detección acotada de contenido exacto repetido entre cabeceras válidas: comparar los datos de negocio normalizados y adicionales, sin origen. Todas las ocurrencias siguen válidas con AVISO_DUPLICADO_EXACTO y grupo común; no se deduplican, fusionan o excluyen. La búsqueda de candidatos por CUF/identidad y su aprobación empresarial siguen pendientes.
- El procesamiento de un lote completado es idempotente. Transacción única de resultados/observaciones; un fallo no deja resultados parciales. Un UPDATE condicionado al estado evita dos ejecuciones simultáneas.

Los campos monetarios/identificadores se serializan como cadenas y las fechas como ISO. La tabla de registros válidos incluye cambios, adicionales, CUF, ANULADO y avisos. La consulta de observaciones añade registro_normalizado como contexto opcional junto al original; conserva las rutas y campos previos de API. No se alteró el DDL.

## Organización de los cambios

| Área | Archivos principales |
|---|---|
| Perfiles DEMO versionados | backend/app/profiles/demostracion.json e __init__.py |
| Lectura con trazabilidad | backend/app/readers/invoices.py |
| Limpieza y repetición exacta | backend/app/services/cleaning.py |
| Cargas, orquestación y limpieza explícita de temporales | backend/app/services/importation.py |
| Transacciones y consultas | backend/app/repositories/lotes.py |
| Endpoints | backend/app/routes/lotes.py y factory existente |
| Interfaz | frontend/src/components/InvoiceWorkspace.tsx, Results.tsx, tipos y cliente HTTP |
| Proxy y ejemplos | frontend/src/app/api/v1/[...path]/route.ts, frontend/public/ y tools/generar_ejemplos.py |
| Pruebas | test_cleaning.py, test_readers.py, test_upload_api.py; regresión de infraestructura existente |

## Arranque local reproducible

Desde la raíz, actualizar dependencias y compilar frontend. No volver a aplicar el SQL sobre la base ya inicializada:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Push-Location frontend
npm.cmd ci
npm.cmd run build
Pop-Location
```

Terminal 1, raíz: iniciar la instancia de prueba existente si está detenida y arrancar Flask:

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' -D .test-data/postgres -l .test-data/postgres.log -o '-p 55439 -h 127.0.0.1' -w start
$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
Set-Location backend
..\.venv\Scripts\python.exe -m flask --app app:create_app run --host=127.0.0.1 --port=8000 --no-debugger --no-reload
```

Terminal 2, raíz:

```powershell
Set-Location frontend
$env:BACKEND_URL='http://127.0.0.1:8000'
$env:PORT='3000'
npm.cmd run start
```

Abrir http://127.0.0.1:3000. Descargar CSV de ejemplo, seleccionarlo con perfil DEMO CSV, cargar y limpiar. Para Excel, seleccionar el perfil correspondiente a fila 1 o fila 4. Los ejemplos Excel se pueden regenerar con `.\.venv\Scripts\python.exe tools/generar_ejemplos.py`.

En un equipo nuevo consultar [preparación de infraestructura](../fase_2_1/README.md). Con Docker disponible se conserva compose.yaml y `docker compose up --build --wait`; el Dockerfile backend instala openpyxl y el frontend copia los ejemplos públicos. No se afirma haber ejecutado las imágenes Docker en este equipo.

## Archivos originales y temporales

- 10 archivos/lote, 10 MiB/archivo, 25 MiB/lote; hasta 5.000 filas de cabecera por lote, 100 columnas y 20 hojas por Excel. XLSX descomprimido hasta 100 MiB, sin macros, cifrado, vínculos externos ni declaraciones DTD/entidades. Son límites técnicos del prototipo, no capacidad/rendimiento medidos para producción.
- Solo archivos admitidos se guardan en backend/temporales/ (o UPLOAD_ROOT configurado), como `<UUID>.bin`. En Docker corresponde al volumen privado /app/temporales. Rechazados conservan metadatos/motivo sin guardar el payload. No hay ruta web para descargar originales.
- Guardado exclusivo, hash SHA-256 y verificación antes de procesar; ninguna escritura sobre el original. Nombres visibles pueden repetirse, las identidades internas no. El lector de Excel abre en read_only y no guarda el libro.
- Acceso: cuenta del backend y administradores del equipo según permisos del SO; directorio privado sin publicación. El parser multipart puede usar temporales del SO, cerrados al terminar la petición. Datos originales/normalizados no se escriben en logs técnicos.
- Vencimiento lógico a 24 h; consultas de lote vencido devuelven 410. No hay borrado automático ni purga al arrancar. Limpieza explícita elimina exclusivamente archivos UUID registrados de lotes vencidos que no estén procesándose, y sus filas por cascada. No borra archivos ajenos ni evidencia vigente.

Ejecutar desde backend/ con las variables de conexión de esa terminal:

```powershell
..\.venv\Scripts\python.exe -m flask --app app:create_app limpiar-cargas-vencidas
```

Originales, temporales, secretos y reportes están ignorados por Git. El prototipo es local/controlado, sin autenticación ni seguridad de producción declarada.

## Pruebas y criterios de aceptación

```powershell
# Desde la raíz; base de prueba dedicada ya inicializada.
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/smoke_connectivity.py
.\.venv\Scripts\python.exe tools/smoke_upload_cleaning.py
Push-Location frontend
npm.cmd run typecheck
Pop-Location
```

Los tests de API/SQL crean esquemas aleatorios y los eliminan al finalizar. Sin TEST_DATABASE_URL, las pruebas que requieren PostgreSQL se omiten explícitamente. Nunca apuntar esa variable a una base empresarial.

| RF/RNF | Prueba/evidencia de esta iteración | Alcance |
|---|---|---|
| RF-01/02 | CSV/Excel filas 1/4, mapeo, libros mixtos, formatos inválidos, carga múltiple y homónimos | Implementado con perfiles DEMO, fuentes reales pendientes |
| RF-07 | Importes exactos, fechas, espacios, ceros, formato numérico Excel y original inmutable | Implementado según perfil; no reglas empresariales inferidas |
| RF-08 | Faltantes, vacíos interiores, tipos, fórmulas y contenido repetido conservado | Parcial: candidatos empresariales avanzados pendientes |
| RF-03/04 | C/P y patrón/catálogo DEMO, desconocidos observados | Apoyo mínimo al estado del registro, catálogo empresarial pendiente |
| RF-09 | Persistencia uniforme de cabeceras con origen | Base parcial, sin agregación ni integración de detalle |
| RF-11/12 | Observaciones con original/normalizado; 5=3+2 y varias incidencias por fila | Consulta y resumen implementados; reporte descargable pendiente |
| RF-05/06 | Consultas API mantienen filtros AND y paginación | Sin interfaz de filtros en esta entrega |
| RNF-01/04/05/06 | Hashes, transacciones/rollback, errores controlados, separación modular, límites y limpieza explícita | Verificado en casos sintéticos; no seguridad integral de producción |
| RNF-02/03 | Sin benchmark de 1.000 filas/fuente ni prueba de aceptación con usuario funcional | No declarar cumplimiento por duración de pytest ni por prueba automatizada del navegador |

### Verificación realmente ejecutada

| Comprobación | Resultado |
|---|---|
| Suite pytest completa con PostgreSQL 17 aislado | **81 passed**, sin omisiones, en **22,50 s** en la ejecución final; no es un benchmark de procesamiento RNF-02 |
| Build de Next.js y comprobación TypeScript | Correctos; cuatro rutas generadas incluyendo proxy de API y health |
| tools/smoke_connectivity.py | Página, estáticos y Next.js→Flask→PostgreSQL: HTTP 200 |
| tools/smoke_upload_cleaning.py | Carga multipart a través de Next.js, limpieza, consulta y contadores: 5=3+2, cinco incidencias, ceros y montos exactos |
| Navegador sin interfaz | Seleccionar archivo, cargar, limpiar, expandir cambios/complementarios y consultar observaciones; sin errores JavaScript |
| Vista escritorio/móvil | 1280 px y 390 px, sin desborde horizontal de página; tabla con desplazamiento propio |
| Originales y fallo parcial | Hashes inmutables; cargas homónimas distintas; rechazo por estructura, rollback de resultados, compensación de archivos y limpieza explícita probados |
| Exportación, datos empresariales y Docker | No se declaran verificados: exportación no implementada, perfiles reales pendientes y contenedores no ejecutados |

[Captura de la demostración con datos ficticios](vista_carga_limpieza.png). El navegador usa herramientas de prueba ya disponibles en el equipo; no se añadió Puppeteer al producto. La demostración HTTP y pytest sí se pueden reproducir con los comandos del repositorio.

La captura y las pruebas usan exclusivamente ejemplos sintéticos. Los procesos de prueba se detienen al terminar; los lotes ficticios creados por smoke conservan sus originales privados hasta la limpieza explícita. Mantener estos tests de regresión junto al entregable.

Documentación técnica contrastada: [cargas y límites Flask](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/), [lectura openpyxl](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html) y [transacciones psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).

## Pendientes y siguiente paso

Confirmar formatos reales/alias, caja/catálogo, validación CUF y política empresarial de duplicidad. Después continuar con filtros de interfaz, consolidación y exportación en su etapa correspondiente; no se implementan en esta entrega por defecto. La limpieza de perfiles de demostración ya permite una demostración funcional sin inventar esos acuerdos.
