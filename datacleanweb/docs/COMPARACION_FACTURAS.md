# Comparar facturas entre archivos

> **Salida disponible desde 2026-11-23:** [filtros de revisión y descargas de registros válidos/observaciones](EXPORTACIONES.md). No cambian las columnas ni reglas de esta comparación; las referencias a exportación pendiente al final describen su entrega original.

> También se admiten los [nueve Excel de «7MO_SEMESTRE/contado o credito»](FORMATOS_FEBRERO.md), incluidos libros con varias hojas/cabeceras y un resumen sin NIT. Reinicia Flask y crea una carga nueva para usar sus perfiles.

Actualización: 2026-11-19. La instrucción reciente del responsable define **número de factura para buscar; NIT/CI y monto numeral para comparar**, con columnas elegidas por archivo. Se revisó `7MO_SEMESTRE/contado o credito/codigo/app.py` como inspiración para los selectores; su unión por NIT + fecha + monto no se adoptó.

## Uso

1. Inicia PostgreSQL, Flask y Next.js siguiendo [los comandos por servicio](INICIAR_SERVICIOS.md). Después de actualizar código, reinicia Flask y recompila/reinicia Next.js.
2. Carga al menos dos archivos .xls/.xlsx/.csv de los formatos admitidos. El reconocimiento conserva los perfiles de hoja y fila de cabecera.
3. En **Comparación entre archivos**, incluye los archivos que quieres revisar. Cada tarjeta permite elegir las columnas reales para factura, NIT/CI y monto. Los alias del perfil solo preseleccionan opciones: puedes cambiarlas. Usa «No disponible» si falta una columna.
4. Elige un archivo de referencia y marca **Comparar NIT/CI**, **Comparar Monto numeral** o ambos.
5. Pulsa **Buscar facturas y comparar**. Esta acción ejecuta primero la limpieza si todavía es necesaria y después compara los originales conservados. No hace falta pulsar antes el botón de limpieza.
6. Revisa una fila por factura y una columna por archivo. Abre **Ver filas de origen** para localizar hoja/fila y sus valores. Filtra coincidencias, diferencias, faltantes, incompletos o varias filas.

Se usa la unión de números de factura de todos los archivos seleccionados: también aparecen facturas ausentes en la referencia. Cambiar la configuración retira el resultado anterior hasta volver a comparar. Paginar o filtrar conserva la configuración aplicada.

## Resultados y reglas

| Estado por archivo | Interpretación |
|---|---|
| Referencia | Una fila localizada en la base, con campos comparables completos |
| Coincide | Una fila encontrada por factura; todos los campos seleccionados equivalen a la referencia |
| Difiere | La factura existe, pero al menos un campo seleccionado es diferente; se indica cuál y el valor de referencia |
| No encontrado | La factura no aparece entre las filas con número comparable del archivo |
| Sin columna de factura | No se puede buscar en ese archivo; no significa ausencia |
| Incompleto | Falta columna/valor, hay un dato ambiguo/fórmula o no existe una referencia única y completa |
| Varias filas | Más de una fila comparte la factura en ese archivo; se conservan sin escoger ganadores ni sumar importes |

**Corrección 2026-11-24:** **Coincidencia exacta** cuenta una factura cuando al menos un archivo distinto de la referencia tiene una fila única y todos los campos seleccionados completos e iguales a una fila única de referencia. Cada factura se cuenta una sola vez, aunque coincida en varios archivos; la referencia no se compara consigo misma para incrementar el contador.

Los contadores y filtros pueden superponerse: una factura puede coincidir con la referencia en un archivo y diferir, faltar o estar incompleta en otro. **Falta en algún archivo** sigue contando las facturas ausentes en cualquiera de los archivos seleccionados, incluida la referencia. No disponer de columna de factura significa incompleto, no ausencia. Se conserva la unión de facturas de todos los archivos y no se modifica el apartado de Revisión.

- La fecha no interviene en búsqueda ni igualdad. Diferencias de NIT/monto no impiden localizar la factura.
- Identificadores: se recortan espacios exteriores y se conservan ceros/interior; se respeta el formato numérico explícito de Excel. Solo una opción desactivada inicialmente permite ignorar ceros de **factura**. El NIT/CI siempre conserva sus ceros.
- Montos: decimal exacto sin redondeo. `151.89` y `151,89` pueden equivaler según el perfil; `1,234` es ambiguo. Fórmulas y vacíos no cuentan como iguales. Comparar negativos finitos no los declara válidos para el negocio: las observaciones de limpieza permanecen.
- La búsqueda incluye registros observados; carecer de C/P o CAJA no la bloquea. No rellena campos ni cambia clasificación.
- El detalle está desmarcado inicialmente. Si lo incluyes, compara valores de fila sin convertirlos en total de factura. Varias líneas de la misma factura quedan ambiguas.
- En SAC se preselecciona **Importe total de la factura**, según confirmación del usuario; no se sustituye por la columna G.
- Las filas sin factura comparable se cuentan por archivo y permanecen en la revisión de registros. «No encontrado» no certifica ausencia dentro de una celda ilegible o sin identificador.
- Números repetidos pueden corresponder a distintas series, emisores o períodos: este mecanismo no certifica identidad fiscal global. No fusiona, elimina, corrige ni exporta filas.
- En grupos grandes, se muestran como máximo 50 filas por archivo/factura, con aviso y cantidad real; todas permanecen en los registros.
- Los nuevos formatos todavía requieren perfil explícito; no se admite automáticamente cualquier libro arbitrario.

## Contrato de API

Nuevo endpoint aditivo: `POST /api/v1/lotes/{id}/comparaciones`, disponible en Flask y en el proxy Next.js. Requiere lote completado y JSON. Ejemplo: sustituir los IDs por los devueltos en la carga.

```json
{
  "archivo_base_id": "UUID_CONTROL",
  "archivos": [
    {"archivo_id": "UUID_CONTROL", "columnas": {"numero_factura": "FACTURA", "nit_ci": "NIT", "monto_numeral": "MONTO"}},
    {"archivo_id": "UUID_SIAT", "columnas": {"numero_factura": "Nº DE LA FACTURA", "nit_ci": "NIT / CI CLIENTE", "monto_numeral": "IMPORTE TOTAL DE LA VENTA"}}
  ],
  "campos": ["nit_ci", "monto_numeral"],
  "ignorar_ceros_factura": false,
  "pagina": 1,
  "tamano": 25,
  "filtro": "todos"
}
```

Columna ausente: `null`. Se validan pertenencia al lote, estado admitido, IDs distintos, columnas reales y roles distintos. Límites: 2–10 archivos, 1–100 resultados/página. Filtros: `todos`, `coincidencia`, `diferencia`, `faltante`, `incompleto`, `ambiguo`.

Respuesta: `datos`, `resumen`, `archivos`, `configuracion`, `configuracion_id`, paginación y muestra limitada de filas sin clave. La configuración no se persiste y la comparación no modifica datos. No se agregaron tablas ni dependencias. Las rutas anteriores, incluida `/relaciones`, se conservan; la pantalla usa la comparación nueva. La metadata `hojas.columnas` expone las cabeceras disponibles tras cargar.

## Verificación reproducible

Corrección del contador del 2026-11-24: **25 pruebas de comparación aprobadas** con PostgreSQL, incluidas ocho nuevas regresiones para coincidencias junto a faltantes, diferencias, datos incompletos, duplicados o columnas ausentes; conteo único por factura; referencia ausente/ambigua/incompleta; y cambio de referencia. Se comprobaron filtros superpuestos y ausencia de modificaciones a los registros de entrada. La prueba de API también verifica que una coincidencia y un dato incompleto puedan contarse simultáneamente. `npm.cmd run typecheck` aprobado. No se repitió la suite completa ni la prueba visual para esta corrección; la evidencia siguiente corresponde a la entrega original.

Desde la raíz, con PostgreSQL de pruebas iniciado:

```powershell
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
```

Los tests de API usan esquemas aislados que se retiran al terminar. `backend/tests/test_comparison.py` usa datos ficticios y verifica diferencias, unión de archivos, ceros, decimales exactos, fórmulas, vacíos, selección de columnas, criterios independientes, ambigüedad, filtros y rechazo de archivos ajenos.

Resultado ejecutado de la suite: **110 pruebas aprobadas**. TypeScript y compilación de producción aprobados. Conectividad HTTP 200 de la página y del proxy de salud con PostgreSQL aprobada.

Prueba ejecutada en navegador con dos libros ficticios: selectores con todas las columnas, procesamiento automático, coincidencias pese a distinta fecha, diferencias de NIT/monto, faltantes, dos filas repetidas conservadas, filtros, cambio de columna, columna no disponible, opción explícita de ceros y vista móvil de 390 px sin desbordamiento global ni errores JavaScript. Los originales de material también se leyeron y compararon en memoria; se verificaron hashes antes/después de los cinco archivos, sin cambios. No se guardaron sus valores de clientes en capturas ni fixtures.

[Captura del flujo probado con datos ficticios](fase_2_2_3/vista_comparacion.png). Al finalizar las pruebas se detuvieron los servidores de Flask y Next.js iniciados para esta revisión. PostgreSQL del proyecto queda iniciado; puedes seguir los comandos de arranque sin reinicializarlo.

Docker no se ejecutó en esta revisión inicial. Resolución automática de conflictos y reglas fiscales globales siguen pendientes. La exportación de registros válidos y observaciones se implementó posteriormente: [entrega 2026-11-23](EXPORTACIONES.md).
