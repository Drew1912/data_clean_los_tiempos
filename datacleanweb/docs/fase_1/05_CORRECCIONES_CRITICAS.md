# Revisión C-01 a C-05 y alcance de Fase 2.1

Fuente: [REVISION_TECNICA_FASE_1.md](../../REVISION_TECNICA_FASE_1.md), instrucciones recientes del usuario y línea base de 12 RF/6 RNF. Solo se atienden críticos/altos. C-06 se prueba por el encargo explícito de Fase 2.1; C-07/C-08/C-09 no se convierten en ampliaciones de esta revisión. Se conservan arquitectura, cuatro tablas y rutas API.

## Estado y evidencia

| Hallazgo | Corrección | Estado honesto |
|---|---|---|
| C-01, RF-01/02/07 | Dos perfiles versionados de referencia Excel/CSV con encabezados del informe, alias explícitos, fila, formato de fecha/decimal y diccionario siguiente | Parcial: lectura de fixtures sintéticos representativos verificable; no hay muestra CSV principal ni validación empresarial del Excel principal. Perfiles no habilitados para datos reales |
| C-02, RF-04/08 | Separar patrón, códigos observados y catálogo admitido; nunca promover coincidencia regex a código válido | Pendiente externo: catálogo empresarial no recibido. Códigos informados 0C/1C no constituyen catálogo completo; 1L/1S siguen sintéticos |
| C-03, RF-08/09/10/11/12 | Distinguir duplicado exacto de candidato, avisos no bloqueantes y errores de calidad; retirar exclusión automática por clave candidata | Propuesta conservadora documentada; política final con Contabilidad pendiente. Sin deduplicación implementada en 2.1 |
| C-04, RF-09/10/11 | Salida mínima y complementaria explícita, conservación de columnas y caso de aceptación de exportación | Contrato documental actualizado; exportación todavía no implementada ni probada |
| C-05, RF-01 a RF-12 | To-Be v2 en BPMN 2.0 XML con colaboración/pool, cuatro carriles, tareas, eventos, compuertas y BPMN DI | Archivo formal importable por formato; validación XSD y referencias registrada al ejecutar pruebas. No ejecución de motor ni importación GUI Camunda acreditada |

## Perfiles conocidos y límites de evidencia

Se inspeccionaron únicamente encabezados y estructura de los Excel locales bajo `../documentaciones/material/`, sin copiar registros ni datos de clientes al repositorio. Los CSV históricos de scripts usan NIT_CLIENTE/FECHA_EMISION/MONTO_TOTAL o NIT_PROVEEDOR/FECHA_COMPROBANTE/TOTAL_BS: son fuentes del cruce antiguo, sin factura/C/P/CAJA suficientes. No se reutilizan como perfiles de cabecera del MVP.

| Estructura encontrada | Hoja / cabecera | Campos presentes | Tratamiento |
|---|---|---|---|
| CONTADO - 2026-2.xlsx | ENERO / fila 4 | CONTRATO (con espacio final), NIT, FACTURA, MONTO, FECHA, CLIENTE, DEPOSITO, PUBLICACION, ENTREGA, REGULARIZACION SISTEMA, NOTA DE COBR. | Referencia conocida sin C/P ni CAJA; no clasificar por «CONTADO» del nombre ni admitir como perfil principal |
| CONTRATOS FACTURADOS 2026-2.xlsx | ENERO / fila 4 | CONTRATO, NIT, FACTURA, MONTO, FECHA, CLIENTE, DEPOSITO, PUBLICACION | Referencia incompleta para obligatorios; no inventar campos faltantes |
| FACTURAS SIAT ENE26 (1).xlsx | hoja1 / fila 1 | FECHA DE LA FACTURA, N° DE LA FACTURA, NIT / CI CLIENTE, CODIGO DE AUTORIZACIÓN, IMPORTE TOTAL DE LA VENTA y columnas tributarias | Otra estructura: no equiparar autorización a CUF ni total de venta a monto numeral sin validación; faltan C/P y CAJA |
| Cabecera principal citada por C-01 | Hoja y fila reales pendientes | NRO FACTURA, FCH. FACTURA, NIT/CI, MONTO NUMERAL, CAJA, C o P | Evidencia del informe, sin archivo representativo disponible; perfiles propuestos bajo perfiles/ |

La fila 4 conocida no demuestra que la cabecera principal esté en fila 4. Se propone variante configurada, nunca escaneo heurístico libre. Los perfiles [Excel](perfiles/cabecera_excel_v1.json) y [CSV](perfiles/cabecera_csv_v1.json) son contratos de lectura de referencia, no lectores productivos ni endpoints habilitados. Hoja Facturas/fila 1 y UTF-8-sig/`;` son convenciones del fixture; requieren evidencia para fuentes reales. La variante Excel fila 4 se comprueba mediante configuración explícita en prueba.

Fecha `%d/%m/%Y`: DD/MM/AAAA solo en el perfil que lo declara, por ejemplo 17/10/2026→2026-10-17; nunca regla universal para otras fuentes. Los perfiles de prueba permiten punto decimal, coma decimal o miles punto/decimal coma solo cuando dan una interpretación única; 1,234 sigue ambiguo sin regla adicional. Las pruebas de esta revisión leen texto/celdas, no implementan normalización del MVP.

## Diccionario de entrada y salida corregido

Estos alias son exactos y explícitos; los citados por el informe tienen evidencia secundaria. Alias adicionales de documentos conocidos se registran como propuestas de mapeo que requieren confirmar equivalencia semántica. No convertir automáticamente tildes, puntuación o similitud en aprobación de otro encabezado.

| Original principal / variante | Canónico, tipo | Obligatorio | Regla / error / origen |
|---|---|---|---|
| NRO FACTURA / propuesta NÚMERO DE FACTURA | numero_factura, texto | Sí | Ceros preservados; faltante bloqueante; original/archivo/hoja/fila conservados |
| FCH. FACTURA / propuesta FECHA DE FACTURA | fecha_factura, fecha ISO | Sí | DD/MM/AAAA solo en perfil explícito; imposible o sin perfil: observar sin adivinar |
| NIT/CI / propuesta NIT / CI | nit_ci, texto | Sí | No float ni eliminación de complementos; catálogo NIT/CI pendiente |
| MONTO NUMERAL | monto_numeral, Decimal | Sí | No usar otra columna MONTO por parecido; formato/rango por perfil y ambigüedades observadas |
| C o P / propuestas C O P y C/P | modalidad_codigo, texto; modalidad derivada | Sí | C/P y valor original; variantes de encabezado requieren habilitación explícita |
| CAJA | caja_codigo, texto; departamento derivado | Sí | Código íntegro; patrón y catálogo admitido de la fuente; desconocido bloquea clasificación |
| RAZON SOCIAL / propuesta RAZÓN SOCIAL | razon_social, texto | No | Espacios seguros; no alterar letras; no llave de identidad |
| CUF | cuf, texto | Pendiente | Conservar incluso sin validador; autorización SIAT no se mapea por defecto a CUF |
| ANULADO | anulado, texto original | Pendiente | Conservar sin filtro ni interpretación de color/estado |
| CONTRATO u otra columna relevante | adicionales, texto/valor exacto | No | Conservar encabezado/valor originales, con prefijo de salida origen__ si no es canónico |
| Metadatos generados | archivo_id, archivo_origen, hoja_origen, fila_origen, linea_fin_origen | Sí según formato | Hoja null CSV, fila física base 1; archivos homónimos inequívocos |
| Diagnóstico derivado | advertencias_duplicidad, grupo_candidato | Cuando aplica | Aviso visible en Excel y reporte; no prueba de fraude ni identidad definitiva |

### Salida mínima y complementaria — C-04

Excel limpio: numero_factura, fecha_factura, nit_ci, monto_numeral, modalidad_codigo (C/P), caja_codigo completo (CAJA), modalidad, departamento y trazabilidad. Complementarias: razon_social, cuf y anulado si existen; todas las columnas originales relevantes de cabecera con `origen__<encabezado>` en caso de columna adicional. No reconstruir encabezados originales solo a partir del canónico: original y adicionales preservan la correspondencia.

Si hay avisos de duplicidad, añadir advertencias_duplicidad y grupo_candidato; no ocultarlos en una hoja distante. Reporte separado incluye también estos avisos y todos los errores con origen/campo/motivo. No fusionar detalles, sumar importes ni descartar columnas relevantes por ser desconocidas. Un campo adicional incompatible con salida segura se informa, sin pérdida silenciosa.

Aceptación futura T10-C04: reabrir Excel exportado y comprobar CUF, ANULADO, CAJA=0C/1C íntegra, C/P, factura/NIT/contrato con ceros, columnas adicionales originales y trazabilidad; detalles fuera del consolidado. Esta prueba sigue propuesta porque no se implementa exportación en 2.1.

## Duplicidad corregida — C-03 / P-06

**Exacto de datos:** dos cabeceras tienen iguales todos los valores de negocio normalizados y columnas complementarias relevantes del mismo perfil semántico, ignorando únicamente metadatos de carga/origen. Diferencia de CUF, ANULADO, emisor/serie cuando existan, importe u otro dato relevante impide llamarlas exactas. Esto prueba repetición de contenido, no necesariamente identidad empresarial; conservar ambas.

**Candidato:** CUF validado coincidente con otros campos diferentes, o clave de respaldo coincidente sin CUF verificado. La clave `(caja_codigo, numero_factura, fecha_factura)` es solo una señal incompleta, no garantía de unicidad. Emisor, serie/sucursal y alcance de numeración deben intervenir cuando existan y estén definidos; no inventarlos. CUF válidos distintos no son duplicados por número coincidente. CUF no verificado no se presenta como válido. Nunca llave NIT+fecha+monto.

**Política provisional segura:** no excluir ni escoger ganador solo por duplicidad, sea exacta o candidata. Las filas que cumplen validaciones independientes permanecen válidas y exportables con avisos visibles y reporte separado; las que tienen errores reales permanecen observadas por esos errores. Códigos `AVISO_DUPLICADO_EXACTO`, `AVISO_POSIBLE_DUPLICADO`, `AVISO_CUF_CONFLICTIVO` son no bloqueantes, almacenados en observacion con tipo/regla/grupo existentes. Los demás errores de validación son bloqueantes. No se añade tabla, columna ni módulo.

Una cabecera puede estar en el Excel válido y tener un aviso en el reporte. `observados` sigue significando filas con al menos un error bloqueante; `cantidad_observaciones_fila` incluye errores y avisos, no se usa para contar cabeceras. `cargados=validos+observados` permanece cierto; válidos pueden tener avisos. La confirmación final de Contabilidad sigue abierta; no se implementa motor de duplicados en esta etapa.

Casos de aceptación futuros T08-C03: copia exacta entre fuentes conserva dos orígenes y ambas filas marcadas; mismo número en series/emisores distintos no se excluye; dos CUF válidos distintos no se fusionan; una misma factura en dos detalles no se compara como cabecera; numeración reutilizada en otra fecha no se excluye; coincidencia de clave sin contexto solo avisa; fila con error y aviso cuenta una vez como observada. No se declaran ejecutados.

## BPMN y trazabilidad

Archivo formal: [to_be_v2.bpmn](diagramas/to_be_v2.bpmn). Mermaid se conserva para discusión. Pool Editorial Los Tiempos; carriles Cajas, Contabilidad, Sistema web (técnico) y Sistemas. `isExecutable=false`: modelo de análisis BPMN 2.0 con DI para importación/modelado, no despliegue de proceso Camunda.

| ID BPMN | Comportamiento | RF |
|---|---|---|
| Task_Cargar / Task_Estructura | Cargar 1..n fuentes, reconocer perfil/encabezado/cabecera-detalle | RF-01/02 |
| Task_ExcluirEstructuras / Gateway_Admitidos | Informar rechazos/hojas detalle sin incorporarlos; permitir revisión de incidencias | RF-02/08/11 |
| Task_Leer / Task_Normalizar | Leer preservando origen y normalizar formatos seguros | RF-07; RNF-01 |
| Task_Clasificar | C/P y CAJA por registro con patrón y catálogo | RF-03/04 |
| Task_Validar / Task_Duplicados | Errores bloqueantes y avisos de duplicidad separados | RF-08/11 |
| Task_Consolidar | Unir cabeceras válidas, incluidas con avisos sin borrar filas | RF-09 |
| Task_Resumen / Task_Revisar | Cantidades disjuntas y consulta | RF-12 |
| Task_Filtros / Task_AplicarFiltros | Modalidad AND departamento, Todos | RF-05/06 |
| Task_Excel / Task_Observaciones / Task_Descargar | Dos salidas trazables en recorrido completo de demostración | RF-10/11/12 |

Los seis CU ya trazados conservan actores y API. El recorrido BPMN genera ambas salidas para mostrar el flujo completo; las rutas de API continúan solicitándolas por separado bajo demanda. No hay conciliación ni cierre contable. El UML formal adicional se pospone: C-05 lo condiciona a exigencia docente, no recibida.

## Fase 2.1

Implementación limitada a frontend Next.js con estado de conexión, GET /api/v1/health Flask que consulta PostgreSQL y verifica las cuatro tablas, Compose con tres servicios, esquema SQL sin cambios y pruebas de conectividad/constraints. Perfiles, duplicados, consolidación, limpieza y exportación siguen siendo diseño; no se incorpora el motor de scripts/ ni endpoints simulados del resto del contrato.
