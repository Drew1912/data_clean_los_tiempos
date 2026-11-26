# Filtros y exportaciones de facturas

> **Regla posterior del responsable:** [modalidad por contrato, sin departamento](MODALIDAD_CONTRATO.md). La interfaz actual solo filtra modalidad; caja/departamento no bloquean válidos del flujo nuevo. La combinación de filtros y clasificación departamental descritas abajo documentan la entrega anterior y su API de compatibilidad histórica.

Entrega: 2026-11-23. Se completa la salida de resultados de RF-05/06/10/11/12: filtrar registros por modalidad y departamento, descargar el consolidado válido y descargar las incidencias del lote. La carga, perfiles, clasificación, login y comparación conservan sus reglas. No se agregan tablas ni migraciones.

## Uso

1. Inicia los servicios e ingresa con admin/admin. Carga archivos y ejecuta **Limpiar y revisar registros**, o utiliza **Buscar facturas y comparar**, que limpia primero cuando corresponde.
2. En **Resultado de la limpieza**, selecciona modalidad y departamento. Se combinan mediante AND: Contado + Cochabamba exige ambas clasificaciones. Los valores desconocidos o ausentes no se completan por el nombre del archivo.
3. La tabla de registros conserva su selector todos/válidos/observados y vuelve a la primera página al cambiar filtros. Los contadores cargados/válidos/observados siguen siendo globales del lote; **Válidos seleccionados** representa lo que entrará en el Excel limpio.
4. **Descargar Excel limpio** genera todas las filas válidas seleccionadas, independientemente del estado visible y de la página actual. Si la selección está vacía, entrega encabezados y contexto, con cero registros.
5. **Descargar observaciones** incluye todas las incidencias del lote, sin filtros de modalidad/departamento. Puede descargarse antes de procesar para revisar rechazos estructurales; se bloquea durante procesamiento.

Los filtros de revisión no cambian las columnas, archivos ni reglas de la comparación. La tabla de comparación no se incorpora como consolidado por coincidencias: las repeticiones se conservan y los detalles observados no se convierten en cabeceras válidas.

## Contenido del Excel

| Hoja | Excel limpio | Reporte de observaciones |
|---|---|---|
| Registros | Canónicos, C/P, CAJA, modalidad, departamento, CUF, ANULADO, archivo/hoja/fila/ID y adicionales `origen__…`; avisos de duplicidad visibles | No aplica |
| Observaciones | No aplica | Una fila por incidencia: archivo/registro, hoja/fila, campo, valor original, tipo, motivo y grupo/regla |
| Originales | Una fila por celda fuente de los registros seleccionados, con nombre de columna, valor y metadatos de tipo/formato | Celdas originales de registros con incidencias; errores estructurales sin registro quedan en Observaciones |
| Cambios | Normalizaciones registradas, con origen y regla | Cambios de registros que tienen incidencias |
| Contexto | Lote, estado, filtros, fecha UTC, cantidad y advertencias | Lote completo, cantidad de incidencias, estado y advertencias |
| Archivos | Identificación, estado y perfil/versión de todos los archivos del lote | Igual, incluidos rechazados |

Los textos se escriben como texto literal, también cuando empiezan por `=`, `+`, `-` o `@`. No se generan fórmulas a partir del contenido importado. Identificadores y originales conservan ceros. Los importes normales se exportan como números; valores con más de 15 dígitos significativos, o que el serializador convertiría a otro valor, se guardan como texto exacto para evitar pérdida de precisión. Originales conserva además el valor fuente.

No se truncan valores. Una celda que exceda el límite de Excel o contenga controles incompatibles genera un error 422 orientativo y conserva el contador anterior. Los reportes se generan en memoria; los temporales internos de openpyxl se retiran al terminar o fallar. No se publican descargas estáticas ni se modifica el original.

## Cantidades y consistencia

`Exportados en el último Excel limpio` corresponde a la última generación limpia que terminó correctamente y guardó sus metadatos. No acumula cantidades entre clics. Cambiar filtros actualiza seleccionados, pero mantiene el dato de la última exportación y muestra sus filtros/fecha. Descargar observaciones no cambia ese contador.

La cantidad exportada acredita generación, no recepción física en el navegador. Un fallo de red después de generar el archivo puede dejar la generación registrada; se puede consultar el resumen y volver a descargar. Un fallo de generación o de transacción conserva la exportación anterior. Las exportaciones del mismo lote se serializan con bloqueo de fila, coordinado con la purga; no quedan metadatos parciales.

## API implementada

- `POST /api/v1/lotes/{id}/exportaciones/limpios`, JSON opcionalmente vacío `{}` o con `modalidad` y `departamento`; defaults todos. No acepta estado, página ni parámetros extra.
- `POST /api/v1/lotes/{id}/exportaciones/observaciones`, cuerpo vacío y sin query parameters.
- Ambas requieren sesión y CSRF. Devuelven XLSX, `Cache-Control: no-store` y `Content-Disposition: attachment` con nombre UUID generado por servidor.
- Limpios añade `X-Registros-Exportados`; observaciones añade `X-Observaciones-Exportadas`. El proxy Next.js conserva esos encabezados y el binario.
- Errores JSON: 400 filtros/cuerpo inválidos, 401 sin sesión, 403 CSRF, 404 inexistente, 409 estado incompatible, 410 vencido, 415 tipo de petición, 422 celda incompatible, 500/503 fallo de generación o dependencia. El cliente comprueba estado/MIME y no descarga errores como Excel.

## Ejecución y verificación

Esta actualización no necesita migración SQL. Reinicia Flask para cargar las rutas. Detén Next.js, ejecuta `npm.cmd run build` en frontend y vuelve a ejecutar `npm.cmd run start`. Recarga la página y crea una carga nueva. [Comandos completos por servicio](INICIAR_SERVICIOS.md).

Con PostgreSQL de pruebas iniciado, desde la raíz:

```powershell
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
```

Verificación ejecutada: **144 pruebas aprobadas en 91,09 s**; TypeScript y compilación de producción aprobados. Las 12 pruebas nuevas cubren matriz AND de 12 combinaciones, selección vacía, más de una página, conservación de repeticiones, campos complementarios y originales, fórmula literal, precisión monetaria, rechazos estructurales, metadatos ante fallo, sesión/CSRF/vencimiento y dos generaciones concurrentes. Pruebas en esquemas PostgreSQL aislados y con datos ficticios.

Tras reforzar la comprobación del serializador monetario, se repitieron las 12 pruebas de exportación: aprobadas en 32,48 s. No se confunde el tiempo de la suite con el benchmark RNF-02 de procesamiento.

Prueba de navegador ejecutada en escritorio y móvil de 390 px, sin errores JavaScript: login, carga de dos CSV ficticios, comparación de siete facturas, filtros AND sin alterar comparación, selección de observados en pantalla y descarga limpia de dos válidos, nueva descarga vacía y reporte completo de 16 incidencias. Los contadores conservaron la generación anterior al cambiar filtros y cambiaron al generar un archivo nuevo. Se reabrieron los tres archivos guardados por el navegador: 2 y 0 filas limpias, 16 incidencias, hojas de trazabilidad, ceros conservados y ninguna fórmula activa. [Captura con datos ficticios](evidencias_cierre/exportaciones.png).

Conectividad HTTP y script de carga/limpieza autenticados también aprobados. Navegador y scripts usaron Flask 18000/Next.js 13000 y un esquema PostgreSQL temporal, sin modificar los lotes del usuario. Los puertos habituales siguen siendo 8000/3000. La ejecución Docker no se probó.

Al terminar se detuvieron los servidores de pruebas y se retiraron el esquema aislado y sus copias privadas temporales; no quedan esquemas de API de prueba. Se conservan capturas ficticias y ejemplos de QA dentro de `.test-data` ignorado. PostgreSQL queda iniciado. El frontend ya quedó compilado en este equipo; para probar la aplicación normal inicia Flask y Next.js según la guía.

Pendientes generales: catálogo empresarial completo, prueba de usabilidad con usuarios y benchmark RNF-02, verificación Docker y recuperación visual de lotes. Completar estas descargas no certifica por sí solo todos los RF/RNF.
