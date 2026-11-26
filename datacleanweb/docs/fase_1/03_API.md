# Contrato propuesto de API REST

> **2026-11-24, usuarios y roles:** [Entrega vigente](../USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **2026-11-24:** [Historial de auditoría](../AUDITORIA.md) implementado con acceso por permiso; seis tablas/68 atributos. GET `/api/v1/auditoria` devuelve eventos paginados; la respuesta de sesión incluye `usuario.puede_ver_auditoria`. Se conservan contratos operativos anteriores.


> **Clasificación por contrato:** POST /lotes/{id}/procesamiento admite JSON `{contratos:[{archivo_id,columna}]}` para el flujo actual sin departamento. Descripción de archivo añade columna_contrato; cuerpo vacío mantiene compatibilidad anterior. [Validaciones y cambio de alcance](../MODALIDAD_CONTRATO.md).

> **2026-11-23:** las dos rutas POST de exportación descritas en este contrato están implementadas. Limpios recibe JSON de filtros, exige lote completado y actualiza ultima_exportacion; observaciones recibe cuerpo vacío, incluye todo el lote y no modifica el contador limpio. Respuesta binaria XLSX con sesión/CSRF y encabezados transmitidos por Next.js. [Contrato vigente, hojas, errores y pruebas](../EXPORTACIONES.md). Las referencias históricas siguientes a exportaciones propuestas/404 quedan superadas por esta entrega.

> **Acceso autorizado 2026-11-19:** las rutas de perfiles/lotes requieren cookie de sesión y los POST además X-CSRF-Token. Se añaden GET /auth/sesion y POST /auth/login, /auth/logout. Salud permanece pública. [Contrato, errores y configuración](../LOGIN_ADMIN.md). La ausencia de autenticación mencionada en el diseño histórico siguiente queda sustituida por esta cuenta única, sin RBAC.

> **2026-11-19:** endpoint aditivo implementado `POST /lotes/{id}/comparaciones` para buscar por factura y comparar columnas NIT/CI/monto seleccionadas por archivo. Descripción de archivo añade `hojas.columnas`; no cambian las tablas ni las rutas previas. [Contrato, ejemplos, validaciones y límites](../COMPARACION_FACTURAS.md).

> Ampliación autorizada para material: .xls, perfil auto por estructura, GET /lotes/{id}/relaciones y parámetro estado=todos|valido|observado en registros (defecto valido). Descripción de archivo añade perfil/nivel y hojas.mapeo. La interfaz pide todos para mostrar incompletos y detalles. [Reglas y límites de correspondencia](../FORMATOS_MATERIAL.md).

Base: `/api/v1`. Implementados health, autenticación, perfiles de demostración y estructuras observadas, carga, consulta, procesamiento, resumen, registros, observaciones, comparación y ambas exportaciones XLSX. Rutas Next.js `/api/v1/*` hacen proxy hacia Flask. JSON UTF-8; importes e identificadores son cadenas, fechas `YYYY-MM-DD`, timestamps ISO UTC. Acceso con administrador único y CSRF, sin permisos diferentes por actor; uso local controlado.

## Convenciones comunes

- Identificadores UUID: las rutas usan UUID válidos; en ejemplos `{lote_id}` representa uno devuelto por carga. Formato inválido: 400; inexistente: 404; vencido aún registrado: 410.
- Filtros canónicos: `modalidad=todos|contado|credito` y `departamento=todos|cochabamba|la_paz|santa_cruz`. Omitidos = todos. Aplicación AND, solo sobre válidos. Opción desconocida y parámetros no admitidos: 400, sin ignorarlos silenciosamente.
- Paginación: `pagina` entero ≥1, `tamano` entre 1 y 100 (defecto 50). Orden estable de carga: posición del archivo en manifiesto, hoja según perfil, fila, id; el orden de archivos/hojas se conserva en metadatos del perfil/lote. No basar orden en UUID aleatorio.
- Respuesta no preparada: 409. JSON de error común: `{ "error": { "codigo": "FILTRO_INVALIDO", "mensaje": "Modalidad no admitida", "campo": "modalidad", "referencia": "incidente_opaco" } }`. Referencia opcional sin datos del cliente; sin rutas privadas, SQL, stack ni valores sensibles en log.
- Respuestas JSON/binarias administrativas: `Cache-Control: no-store`; no guardar reportes en caché pública. Exportaciones devuelven `Content-Disposition: attachment` con nombre generado por servidor.

| Endpoint | Método / petición | Éxito | Errores específicos | RF/RNF |
|---|---|---|---|---|
| `/health` | GET, sin cuerpo | 200 `{estado:"ok",db:"ok"}` | 503 dependencia indisponible | RNF-04/05 |
| `/perfiles` | GET | 200 perfiles/versiones habilitados y parámetros de lectura visibles | 503 configuración inválida | RF-01/02 |
| `/lotes` | POST multipart archivos + manifiesto | 201 lote, archivos admitidos/rechazados y advertencias | 400 manifiesto, 413 tamaño/número, 503 almacenamiento/DB | RF-01/02 |
| `/lotes/{id}` | GET | 200 estado, fuentes y vencimiento | 400/404/410 | RF-01/12 |
| `/lotes/{id}/procesamiento` | POST, cuerpo vacío | 200 resumen; si completado reutiliza resultado | 409 sin admitidos, procesando o fallido; 500/503 ejecución | RF-03/04/07/08/09/12 |
| `/lotes/{id}/resumen` | GET, filtros opcionales | 200 contadores, selección y última exportación | 400 filtros; 404/410 | RF-12; RF-05/06 |
| `/lotes/{id}/registros` | GET filtros + paginación | 200 válidos seleccionados con origen, total y página | 400 parámetros; 409 no completado | RF-05/06/09 |
| `/lotes/{id}/observaciones` | GET pagina/tamano, sin filtros administrativos | 200 incidencias de todo el lote y referencia a fila original | 400 paginación; 404/410 | RF-08/11 |
| `/lotes/{id}/exportaciones/limpios` | POST JSON filtros | 200 binario XLSX completo de válidos seleccionados | 400 JSON/filtros; 409 no completado; 500 generación | RF-10/12 |
| `/lotes/{id}/exportaciones/observaciones` | POST, cuerpo vacío | 200 binario XLSX con todas las incidencias del lote | 404/410; 500 generación | RF-11 |

No hay endpoints de edición de registros, aceptación de duplicados, conciliación ni administración de usuarios/perfiles. La consulta y exportación de observaciones funcionan con rechazos de carga, aunque el lote no se haya procesado; durante procesamiento la exportación responde 409.

## 1. Perfiles disponibles

`GET /api/v1/perfiles` devuelve, por ejemplo:

```json
{
  "datos": [{
    "id": "demo_cabecera_csv_f1",
    "version": "1",
    "descripcion": "Cabecera sintética CSV",
    "nivel": "cabecera",
    "extensiones": [".csv"],
    "fila_encabezado": 1,
    "encoding": "utf-8-sig",
    "delimitador": ";",
    "formato_numerico": "decimal_coma",
    "sintetico": true
  }]
}
```

Perfiles Excel fila 1/fila 4 y detalle reconocido se listan aparte; no se ofrece perfil real sin evidencia. El cliente no manda regex ni reglas arbitrarias; solo un perfil habilitado. Modificaciones de reglas se versionan en backend, no mediante API nueva.

## 2. Crear lote

Multipart con partes binarias repetidas `archivos` en orden y parte `manifiesto` JSON. Relacionar por índice, nunca solo por nombre (pueden existir homónimos):

```json
{
  "archivos": [
    {"indice": 0, "perfil_id": "demo_cabecera_csv_f1", "perfil_version": "1"},
    {"indice": 1, "perfil_id": "demo_cabecera_xlsx_f4", "perfil_version": "1"}
  ]
}
```

Cada índice aparece exactamente una vez y cubre todas las partes. Perfil/version inexistente produce rechazo de ese archivo con motivo; manifiesto ilegible/incompleto produce 400 sin lote. Archivo corrupto, extensión no admitida, firma incompatible, hoja detalle o columnas inválidas se informan por fuente, sin inventar filas. No ejecutar fórmulas, vínculos ni macros.

201 de ejemplo (símbolos `{lote_id}`/`{archivo_id}` son marcadores, no UUID literales para copiar):

```json
{
  "lote_id": "{lote_id}",
  "estado": "cargado",
  "vence_en": "2026-11-18T16:00:00Z",
  "archivos": [
    {"id": "{archivo_a}", "indice": 0, "nombre": "demo.csv", "estado": "admitido", "hojas": [{"nombre": null, "nivel": "cabecera", "estado": "admitida", "fila_encabezado": 1}]},
    {"id": "{archivo_b}", "indice": 1, "nombre": "detalle.xlsx", "estado": "rechazado", "motivos": ["ESTRUCTURA_DETALLE_FUERA_MVP"]}
  ],
  "advertencias": ["Un archivo no se incorporará al consolidado"],
  "puede_procesar": true
}
```

201 indica lote registrado, no todos sus archivos aceptados. Incluso si todos se rechazan, devolver lote revisable, puede_procesar=false y reporte de estructura disponible. Exceso de límites globales: 413 antes de crear lote, limpiar residuos del intento. Propuestas de límites en P-12; el máximo HTTP admite margen de multipart por encima de 25 MiB de contenido.

## 3. Procesar y consultar resumen

`POST /lotes/{id}/procesamiento`: síncrono; devuelve el mismo objeto de resumen de GET al finalizar. No usar 202 ni estados ficticios de tarea en cola. El cliente deshabilita el botón mientras espera; refresca estado si pierde conexión. Estado completado se puede consultar sin repetir trabajo.

Resumen de fixture: seis cabeceras válidas C/P×1C/1L/1S, más fecha imposible, modalidad X y vacío interior (nueve filas cargadas). `GET /lotes/{id}/resumen?modalidad=contado&departamento=cochabamba` antes de exportar:

```json
{
  "lote_id": "{lote_id}",
  "estado": "completado",
  "registros": {"cargados": 9, "validos": 6, "observados": 3, "seleccionados": 1, "exportados": 0},
  "archivos": {"recibidos": 2, "admitidos": 2, "rechazados": 0},
  "cantidad_observaciones_fila": 3,
  "cantidad_observaciones_estructura": 0,
  "filtros": {"modalidad": "contado", "departamento": "cochabamba"},
  "ultima_exportacion": null,
  "advertencias": ["Perfiles sintéticos; CUF y ANULADO sin validación especializada"]
}
```

Después de exportación limpia correcta: exportados=1 y `ultima_exportacion={cantidad:1,modalidad:"contado",departamento:"cochabamba",generado_en:"..."}`. Cambiar filtros no altera esa cantidad histórica; seleccionados se recalcula para los filtros actuales. La interfaz rotula «Exportados en el último archivo». El registro de exportación acredita generación del archivo, no recepción física.

Antes de procesamiento: `registros` tiene esos cinco campos con null, `ultima_exportacion=null`; los conteos de archivos/observaciones estructurales sí son conocidos. Fallo de procesamiento no presenta ceros como lote exitoso. RF-12 se evalúa para lotes completados.

## 4. Resultados paginados

`GET /lotes/{id}/registros?modalidad=contado&departamento=cochabamba&pagina=1&tamano=50`:

```json
{
  "datos": [{
    "id": "{registro_id}",
    "numero_factura": "000101",
    "nit_ci": "00012345001",
    "fecha_factura": "2026-10-15",
    "monto_numeral": "151.89",
    "razon_social": "Cliente Sintético Alfa",
    "modalidad_codigo": "C",
    "caja_codigo": "1C",
    "modalidad": "contado",
    "departamento": "cochabamba",
    "cuf": null,
    "anulado": null,
    "adicionales": {},
    "cambios": [],
    "origen": {"archivo_id": "{archivo_id}", "archivo": "demo.csv", "hoja": null, "fila": 2, "linea_fin": 2}
  }],
  "pagina": 1,
  "tamano": 50,
  "total": 1
}
```

Página fuera del total: 200 con datos=[] y total real. Monto Decimal se serializa como string, no número JSON float. La consulta de válidos no devuelve filas observadas; la vista observaciones incluye el contexto necesario de la fila conservada.

## 5. Observaciones

`GET /lotes/{id}/observaciones?pagina=1&tamano=50` devuelve `{datos:[...],pagina,tamano,total}`. Cada elemento:

```json
{
  "id": 1,
  "registro_id": "{registro_id}",
  "tipo": "FECHA_INVALIDA",
  "campo": "fecha_factura",
  "motivo": "La fecha no existe en el calendario",
  "valor_original": "2026-02-30",
  "grupo_candidato": null,
  "regla": "fecha_iso_v1",
  "origen": {"archivo_id": "{archivo_id}", "archivo": "demo.csv", "hoja": null, "fila": 8, "linea_fin": 8},
  "registro_original": {"Fecha de factura": "2026-02-30", "Número de factura": "000107"}
}
```

En incidencia de archivo/hoja, registro_id/fila/campo pueden ser null. Códigos propuestos: ARCHIVO_INVALIDO, PERFIL_DESCONOCIDO, COLUMNAS_INVALIDAS, ESTRUCTURA_DETALLE_FUERA_MVP, FILA_VACIA, CAMPO_OBLIGATORIO, FECHA_INVALIDA, MONTO_AMBIGUO, MODALIDAD_DESCONOCIDA, CAJA_DESCONOCIDA, CUF_INVALIDO, POSIBLE_DUPLICADO. No exigir tipo numérico universal para CI mientras no haya regla confirmada.

Corrección C-03: los tipos AVISO_DUPLICADO_EXACTO, AVISO_POSIBLE_DUPLICADO y AVISO_CUF_CONFLICTIVO usan la estructura existente. No excluyen por sí solos del Excel válido; se muestran allí y en el reporte. observados cuenta solo filas con errores bloqueantes; cantidad_observaciones_fila incluye también avisos, sin alterar rutas ni campos.

Advertencias no bloqueantes sobre configuración (CUF sin validador, ANULADO no interpretado) se derivan de snapshots y aparecen en `advertencias`; no crean una observación de fila por cada registro. Esto conserva la ecuación disjunta de válidos/observados.

## 6. Excel limpio y reporte separado

`POST /lotes/{id}/exportaciones/limpios`, JSON:

```json
{"modalidad": "contado", "departamento": "cochabamba"}
```

Valores omitidos = todos; JSON mal formado, campo inesperado o filtro no admitido: 400. Éxito:

```text
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="consolidado_<id>.xlsx"
Cache-Control: no-store
X-Registros-Exportados: 1
```

Hoja `Registros`: canónicos, modalidad/departamento, CUF/ANULADO disponibles, adicionales prefijadas y trazabilidad completa. Hoja `Contexto`: id de lote, perfiles/versiones, filtros, fecha y advertencias de reglas pendientes. Incluir avisos/grupo de duplicidad cuando corresponda; [salida C-04](05_CORRECCIONES_CRITICAS.md). Una fila por cabecera válida seleccionada; sin eliminación ni agregación por coincidencia. Exportación incluye todos los seleccionados, no solo la página mostrada. Textos se escriben como celdas texto para impedir fórmulas activas; identificadores conservan ceros. Si no hay coincidencias, generar encabezados y registrar exportados=0.

`POST /lotes/{id}/exportaciones/observaciones`: mismo MIME, `filename="observaciones_<id>.xlsx"`. Hoja `Observaciones`: una fila por incidencia, origen, campo, motivo, tipo, dato original contextual y grupo/regla de candidato; hoja `Contexto` para advertencias/archivos excluidos. Puede incluir varias incidencias por cabecera: no se confunde con cantidad de observados. No aplica filtros administrativos que oculten errores y no modifica exportados de datos limpios.

## Errores transversales

400 petición/UUID inválido; 404 lote inexistente; 409 estado incompatible; 410 vencido; 413 límites; 415 Content-Type de petición incorrecto (JSON/multipart según ruta); 500 fallo interno; 503 DB/almacenamiento indisponible. Una extensión no admitida de un archivo es incidencia del lote, no un 415 del multipart completo. Los clientes comprueban status y MIME antes de descargar; un error JSON nunca se ofrece como .xlsx.
