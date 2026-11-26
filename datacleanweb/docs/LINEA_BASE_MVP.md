# Línea base funcional — decisiones del usuario

Fecha: 2026-11-17. Síntesis del adjunto «He revisado los documentos de la Fase 0…» recibido con la solicitud de revisar rutas de PROMPT.md. Conserva las decisiones dentro del proyecto; no modifica los 12 RF ni los 6 RNF.

1. Importar Excel/CSV, limpiar, clasificar, consolidar válidos, filtrar y generar Excel. Excluidos conciliación histórica, SAC, edición y administración avanzada de usuarios.
2. C o P: C=Contado, P=Crédito. CAJA: C=Cochabamba, L=La Paz, S=Santa Cruz. Ejemplos comunicados 1C/0C. Conservar código completo; proponer patrón configurable de letra final sin aceptar códigos no documentados. Clasificación incierta: observaciones.
3. Cabecera obligatoria: factura, fecha de factura, NIT/CI, modalidad, caja, monto numeral. Razón social complementaria; CUF/ANULADO conservados si existen, tratamiento y obligatoriedad pendientes. Identificadores textuales, fechas ISO, montos exactos; sin inventar ni resolver ambigüedades.
4. Una fila de cabecera por factura; reconocer detalle aparte, sin mezclar ni borrar líneas repetidas legítimas. Integración cabecera-detalle posterior.
5. Posibles duplicados: priorizar CUF presente y válido; en ausencia usar combinación documentada de identificadores. No eliminar registros; conservar archivo/hoja/fila.
6. Perfiles configurables .xlsx/.csv con cabecera en fila 1 o 4; CSV declara encoding/delimitador/formato numérico. Desconocidos: informar, sin interpretación arbitraria.
7. Modalidad y departamento con opción Todos y condición AND. Clasificar por registro, nunca por nombre de archivo.
8. Excel válido filtrado y reporte separado archivo/hoja/fila/campo/motivo. Resumen cargados/válidos/observados/exportados sin duplicar filas con varios errores.
9. Cajas carga/filtra; Contabilidad procesa/consulta/exporta; Sistemas soporta/verifica incidencias. Interacciones conceptuales sin autenticación/RBAC.
10. Actualizar decisiones confirmadas/provisionales/evidencia; To-Be v2 de limpieza/clasificación/consolidación/filtros; conservar As-Is; no alterar requisitos silenciosamente.
11. Iniciar únicamente Fase 1: arquitectura, CU, secuencias, dominio, ER/persistencia mínima, API, mockups, carpetas y trazabilidad. Sin implementación completa ni ampliación de alcance; documentar impacto de pendientes.

## Revisión de rutas y precedencia

PROMPT.md actualizado referencia correctamente `docs/DCU.png`, `docs/DCU.drawio`, `docs/diagrama_as_is.png`, `docs/diagrama_to_be.png`, el Word en `docs/` y `docs/reglas_de_validacion.md`. Se volvieron a leer/inspeccionar. Son los diagramas históricos existentes con rutas corregidas; no aparecieron archivos adicionales. As-Is, To-Be y DCU originales se conservan intactos.

Persiste una diferencia: PROMPT.md referencia `docs/REQUISITOS.md`, pero el archivo físico es [REQUSITOS.md](REQUSITOS.md). Se usa el existente sin renombrar ni modificar requisitos. Los `.bpmn` y `REGLAS_DE_NEGOCIO.md` ya no aparecen como fuentes exigidas en la sección actualizada; no son bloqueos.

La orden reciente de iniciar Fase 1 prevalece sobre la instrucción inicial de comenzar por Fase 0. Las interacciones recientes prevalecen sobre asociaciones ambiguas del DCU. La conciliación en reglas_de_validacion.md y To-Be histórico sigue excluida. Las propuestas iniciales de Fase 0 quedan sustituidas donde esta línea base o Fase 1 lo indiquen.

Cambios: registro de decisiones actualizado, adenda en Fase 0 y entregables bajo `docs/fase_1/`. RF/RNF, PROMPT y diagramas fuente sin cambios.
