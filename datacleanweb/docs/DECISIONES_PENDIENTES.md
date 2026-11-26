# Decisiones funcionales — línea base y pendientes

> **2026-11-24, usuarios y roles:** [Entrega vigente](USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **Actualización 2026-11-24:** [Auditoría implementada](AUDITORIA.md): historial persistente de accesos y operaciones, permiso de consulta comprobado en Flask y nueva página en el menú. Migración 005; el modelo vigente tiene 6 tablas y 68 atributos. Las referencias anteriores a ausencia de historial o cinco tablas describen entregas previas.


> **2026-11-23 — nueva regla confirmada:** el responsable indica columna de contrato seleccionable por archivo; prefijo P = Crédito, C = Contado; pide dejar de lado departamento por falta de fuente fiable. Se modifica RF-03 operativamente y se retiran RF-04/06 del alcance actual, conservando los RF originales como antecedente. Migración 004 elimina la obligatoriedad de caja/departamento sin borrar columnas/datos; lotes anteriores no se reclasifican automáticamente. [Regla, compatibilidad y pruebas](MODALIDAD_CONTRATO.md). El alcance modificado debe explicarse en la entrega académica; no se presenta como cumplimiento de los RF retirados.

> **2026-11-23 — filtros y salida autorizados:** el usuario aprobó continuar con filtros combinados, Excel limpio y observaciones. Se implementan sobre las cinco tablas existentes; comparación conserva sus criterios. Observaciones siempre abarca el lote, y exportados identifica la última generación limpia correcta, sin acumular ni acreditar recepción física. Importes fuera de 15 dígitos significativos se exportan como texto exacto para evitar pérdida en Excel. [Implementación y pruebas](EXPORTACIONES.md). Catálogos, benchmark y aceptación humana siguen pendientes.

> **2026-11-19 — cierre académico:** el responsable solicitó expresamente login admin/admin y evaluación de ACTI_FINAL.md. Autoriza ampliar el límite de autenticación del PROMPT con una sola cuenta persistida y sesión real, sin RBAC/gestión de usuarios. Contradicción concreta con el DER anterior de cuatro tablas: no representaba credenciales ni autor; se añade usuario y lote.creado_por nullable mediante migración 003, conservando lotes previos sin atribuirles autor. No autoriza CRUD manual de facturas ni declara completadas exportaciones o pruebas humanas. [Decisión técnica](LOGIN_ADMIN.md), [estado por actividad](REVISION_ACTIVIDAD_FINAL.md).

> **2026-11-19 — nuevas fuentes autorizadas:** la solicitud de usar los Excel de `7MO_SEMESTRE/contado o credito` habilita perfiles de esas estructuras observadas. Se documentan cabeceras por hoja, etiquetas complementarias repetidas y dimensiones Excel infladas. El resumen sin NIT se admite sin inventarlo; SAC febrero usa su MONTO NUMERAL explícito sin cambiar la decisión anterior de importe del SAC .xls. Emisor/serie, agregación de detalle y catálogo empresarial completo siguen pendientes. [Evidencia y pruebas](FORMATOS_FEBRERO.md).

> **2026-11-19 — nueva aclaración del responsable:** se autoriza búsqueda configurable entre archivos por **número de factura**, comparando **NIT/CI y/o monto numeral**. La fecha deja de formar parte de la llave en esta función. Sustituye la propuesta previa de correspondencias como flujo principal y el límite histórico que excluía esta comparación; no autoriza conciliación contable avanzada. Columnas y referencia se eligen por carga, sin completar/eliminar/fusionar datos ni agregar tablas. Varias filas por factura se informan como ambiguas; la identidad fiscal por emisor/serie y la agregación de detalle siguen pendientes. [Decisión, API, reglas y pruebas](COMPARACION_FACTURAS.md). Los RF/RNF originales se conservan; esta ampliación tiene autorización conversacional explícita.

> Actualización por solicitud posterior: el usuario indicó usar los cinco Excel de material, confirmó que necesita tanto mapeo como relaciones entre archivos y añadió .xls. Confirmó que en la cabecera SAC el importe proviene de «Importe total de la factura», no de G/cabecera 1. [Evidencia, cambios y pruebas](FORMATOS_MATERIAL.md). Se habilitan perfiles de estructuras observadas; siguen pendientes un catálogo empresarial completo y políticas de agregación. Las correspondencias son candidatos sin completamiento automático ni conciliación NIT+fecha+monto. Esta decisión supera el límite anterior de solo demostración y permite relacionar detalle como referencia, sin integrarlo al consolidado de cabeceras.

Actualización: 2026-11-17. Evidencia: instrucciones del usuario adjuntas en este turno, registradas en [LINEA_BASE_MVP.md](LINEA_BASE_MVP.md). Prevalecen sobre propuestas anteriores. Confirmado por el usuario no equivale a validación empresarial independiente. Se conservan los identificadores P de Fase 0.

## Confirmado por el usuario

| Tema | Decisión | Referencias |
|---|---|---|
| Alcance | Importación Excel/CSV, limpieza, clasificación, consolidación de válidos, filtros AND y Excel; fuera conciliación histórica, SAC, edición y administración avanzada de usuarios | 12 RF y 6 RNF sin cambios; adjunto §§1/7 |
| P-01, parcial | C/P define modalidad; CAJA define C/L/S. Conservar código completo; letra departamental final mediante perfil sin aceptar códigos no documentados; ejemplos informados 1C/0C | RF-03/04; adjunto §2 |
| P-02, parcial | Cabecera: factura, fecha, NIT/CI, modalidad, caja y monto numeral obligatorios; razón social complementaria; conservar CUF y ANULADO disponibles | RF-02/07/08; adjunto §3 |
| P-03, parcial | Identificadores textuales, fechas ISO, decimales exactos; sin inventar ni resolver ambigüedades | RF-07; adjunto §3 |
| P-06, granularidad | Una fila de cabecera representa una factura. Reconocer detalles como estructura diferente; no mezclar ni eliminar líneas. Integración completa diferida | RF-08/09; adjunto §4 |
| P-06, candidatos | Priorizar CUF presente y válido; sin él proponer combinación de identificadores; no eliminar ocurrencias; conservar origen | RF-08/11; adjunto §5 |
| P-07, parcial | Perfiles .xlsx/.csv, encabezados 1 y 4, encoding/delimitador/formato numérico explícitos; desconocidos se informan | RF-01/02; adjunto §6 |
| Salidas/P-08, parcial | Excel válido filtrado y reporte separado con archivo/hoja/fila/campo/motivo; cantidades sin contar dos veces filas con varios errores | RF-10/11/12; adjunto §8 |
| P-10 | Cajas carga/filtra; Contabilidad procesa/consulta/exporta; Sistemas soporta/verifica problemas técnicos; sin autenticación/RBAC | Adj. §9; sustituye asociaciones ambiguas del DCU previo |
| Siguiente fase | Registrar línea base e iniciar solo análisis/diseño de Fase 1 | Adj. §§10/11; sin implementación completa |

## Propuestas provisionales de diseño

Se usan para hacer revisable el diseño y probar con datos sintéticos; no son reglas empresariales aprobadas.

| ID | Propuesta concreta | Impacto y verificación |
|---|---|---|
| P-01 | Expresión configurable `^(?P<numero>[0-9]+)(?P<departamento>[CLS])$` más lista explícita de códigos por perfil. Coincidir con el patrón no basta: también debe pertenecer a la lista | 1C/0C son ejemplos comunicados, no catálogo completo. Demostración admite 0C/1C/1L/1S sintéticos; 1L/1S necesitan evidencia para fuente real. C/L/S solos únicamente en perfil sintético explícito |
| P-03 | Recortar extremos, conservar interior y ceros; no aplicar solo dígitos a todos los CI | Evita destruir complementos; patrón real pendiente |
| P-04 | Importe ≥0 y hasta dos decimales en demostración; ambiguos/exceso de escala observados sin redondear; PostgreSQL NUMERIC sin escala fija | Moneda, signo, escala y límites empresariales pendientes |
| P-05 | ISO en fixtures; otros formatos declarados en perfil; sin filtro temporal/exclusión por periodo | No ampliar RF-05/06 |
| P-06 | C-03 retira la exclusión automática: distinguir exactos de candidatos; conservar toda ocurrencia; avisos permanecen en Excel válido marcado si pasan demás validaciones. CUF verificable prioritario, clave alternativa solo señal contextual | No garantiza identidad global. Sin validador CUF: conservarlo y usar clave alternativa con advertencia visible de lote; CUF explícitamente inválido se observa. Completar alcance emisor/serie con evidencia |
| P-07 | Pruebas CSV UTF-8-sig, `;`, decimal declarado; Excel encabezado 1 o 4 explícito; sin búsqueda libre de cabecera | Alias/hojas/pies reales pendientes. Detalle identificado se informa fuera del consolidado sin alterar origen |
| P-08 | Contar cabeceras: cargados=válidos+observados; vacíos interiores observados, espacio final no contado. Exportados=cantidad de última exportación limpia generada correctamente con sus filtros, sin acumular | Sustituye propuesta inicial de reiniciar exportados al filtrar. Seleccionados se muestra aparte; no afirmar recepción física del archivo en navegador |
| P-09 | Continuar archivos admitidos, mostrando rechazos por archivo/hoja; si no hay cabeceras, no completar proceso; selección vacía permite Excel con encabezados | Detalles/rechazos fuera del conteo de cabeceras |
| P-12 | Uso local; archivos privados y vencimiento lógico de lotes a 24 h. En carga/limpieza se adopta limpieza explícita por CLI de vencidos, sin borrado automático al iniciar. Límites: 10 archivos, 10 MiB/archivo, 25 MiB/lote, 100 MiB descomprimidos/Excel | Cambio operativo provisional documentado en Fase 2.2/2.3; no política empresarial confirmada. Benchmark RNF-02 sigue pendiente |

## Evidencia todavía necesaria

| ID | Falta concreta | Cuándo afecta |
|---|---|---|
| P-01 | Catálogo real y excepciones a letra final; vigencia 0C/1C | Antes de fuentes reales |
| P-02 | Encabezados/alias y muestras anonimizadas cabecera/detalle; obligatoriedad y formato CUF/ANULADO | Reconocimiento real y reglas especializadas |
| P-03 | Tipos y patrones de identificación, incluidos complementos CI | Antes de validadores empresariales |
| P-04 | Monto numeral real, moneda, negativos/escala | Antes de declarar importes reales válidos |
| P-05 | Formatos de fecha y rango, si procede | Antes de interpretar fechas no ISO; filtro por periodo requiere decisión |
| P-06 | Validación CUF, emisor/sucursal/serie, clave alternativa; confirmar política final de avisos/candidatos en Excel; exclusión automática anterior retirada | No se asegura unicidad global ni deduplicación definitiva |
| P-07 | Perfiles reales de lectura, hojas/pies y reconocimiento fiable de detalle | Formato desconocido se rechaza explícitamente |
| P-08/09 | Convenciones de conteo, exportación y lotes parciales | Antes del cierre de aceptación |
| P-11 | Vigencia empresarial de reglas heredadas; PNG ya localizados, BPMN editables ya no exigidos por PROMPT actualizado | No bloquea diseño; conciliación sigue excluida |
| P-12 | Equipo benchmark, acuerdo de retención/acceso y límites | Antes de verificación RNF y uso con datos reales |

## Actualización por revisión técnica C-01 a C-05

Fuente: REVISION_TECNICA_FASE_1.md y solicitud reciente. Se autoriza solo infraestructura 2.1 tras correcciones críticas/altas, sin procesamiento completo. P-01: patrón más catálogo, pero catálogo admitido confirmado vacío; no promover ejemplos a aprobación. P-02/P-07: encabezados principales citados por informe y estructuras Excel conocidas documentados; perfiles Excel/CSV de referencia no habilitados para datos reales. CSV principal, semántica/hoja/fila empresariales aún requieren evidencia.

P-06/C-03: se retira la exclusión automática. Exactitud de contenido y sospecha de identidad son categorías diferentes; ambas conservan entradas. Propuesta no bloqueante en [correcciones](fase_1/05_CORRECCIONES_CRITICAS.md); aprobación de Contabilidad pendiente.

C-04: salida mínima/complementaria y T10-C04 definidos, exportación funcional pendiente. C-05: [BPMN formal](fase_1/diagramas/to_be_v2.bpmn) es la entrega BPMN; Mermaid queda para discusión. C-06 se verifica por encargo 2.1; retención/purga no se implementan en infraestructura mínima.

P-10 resuelta para este diseño por instrucciones recientes. Las demás decisiones parciales conservan su evidencia faltante. Registrar nuevas resoluciones con fecha, responsable, respuesta, archivos y pruebas afectados; nunca sobrescribir RF/RNF silenciosamente.

## Actualización 2026-11-18 — carga y limpieza

El usuario autorizó comenzar carga/limpieza aprovechando scripts/. Esta indicación sustituye el límite anterior de solo infraestructura para la nueva iteración. [Entregable Fase 2.2/2.3](fase_2_2_3/README.md): perfiles DEMO configurados, carga múltiple, lectura sin inferencia numérica, limpieza exacta y observaciones persistidas; cuatro tablas y rutas conservadas.

P-01/P-02/P-07 empresariales siguen abiertos. Solo se habilitan tres perfiles sintéticos, no los perfiles reales de referencia deshabilitados. La clasificación C/P y patrón+catálogo DEMO sirve al estado válido exigido por el esquema; no aprueba cajas de fuentes reales.

P-06: solo se implementa aviso de contenido exacto repetido, sin excluir filas. Candidatos por identidad, validación CUF y política empresarial final siguen pendientes. Se conserva CUF/ANULADO sin interpretación; AVISO_VALOR_NO_INTERPRETADO identifica complementarios que requieren revisión y no bloquea por sí solo una cabecera.

P-12: guardado privado/hash, vencimiento lógico 24 h y eliminación explícita por comando, sin purga automática. El ajuste simplifica operación del prototipo y mantiene evidencia hasta que se ejecute limpieza; límites y acceso descritos en el entregable. Exportaciones y filtros de interfaz se reservan para las siguientes iteraciones.

## Decisión del responsable — 2026-11-24: historial y acceso

Se autoriza expresamente guardar accesos, fechas, usuario y cambios del sistema y limitar su consulta a usuarios autorizados, inicialmente admin. Se implementa un permiso booleano y tabla de eventos, conservando la cuenta única; no se incorpora un gestor de usuarios ni roles. Esta ampliación prevalece sobre la restricción previa de no añadir módulos. Retención de auditoría, respaldos y gestión de varias cuentas continúan pendientes de definición; no se inventa una política empresarial ni se reconstruyen eventos anteriores.
