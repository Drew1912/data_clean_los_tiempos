# Fase 1 — Análisis y diseño mínimo

> **2026-11-24:** [Historial de auditoría](../AUDITORIA.md) implementado con acceso por permiso; seis tablas/68 atributos. GET `/api/v1/auditoria` devuelve eventos paginados; la respuesta de sesión incluye `usuario.puede_ver_auditoria`. Se conservan contratos operativos anteriores.


> **DER vigente 2026-11-19:** cinco tablas, incluida `usuario` y la autoría de cada lote. [Explicación para el caso de estudio](../DER_ACTUAL.md) · [diccionario](02_DATOS.md) · [SVG](diagramas/entidad_relacion.svg) · [PNG](diagramas/entidad_relacion.png). La implementación admite la cuenta única admin; las referencias a cuatro tablas y ausencia de login siguientes corresponden a decisiones históricas ya sustituidas por la ampliación autorizada.

> Estado de desarrollo posterior: [carga y limpieza Fase 2.2/2.3](../fase_2_2_3/README.md), incluyendo reutilización de scripts/, límites, pruebas y pendientes de perfiles reales.

> Actualización por revisión técnica: [correcciones críticas/altas C-01 a C-05](05_CORRECCIONES_CRITICAS.md), [BPMN 2.0 formal](diagramas/to_be_v2.bpmn) y [resultados reales de Fase 2.1](../fase_2_1/README.md). Las afirmaciones de «sin aplicación/SQL ejecutado» siguientes describen la entrega original, no el estado actualizado. Arquitectura, rutas API y cuatro tablas conservadas; la política de exclusión de candidatos se retira por C-03.

Fecha: 2026-11-17. Entrega documental; no hay aplicación implementada, DDL ejecutado ni benchmark. Base: [decisiones del usuario](../LINEA_BASE_MVP.md), [12 RF y 6 RNF](../REQUSITOS.md), PROMPT.md releído, Word, DCU.png/.drawio, As-Is/To-Be PNG y reglas_de_validacion.md. Se mantienen las exclusiones del MVP.

| Entregable | Archivo | Cobertura |
|---|---|---|
| Arquitectura, To-Be v2, casos de uso, secuencias y dominio | [01_DISENO.md](01_DISENO.md) | RF-01 a RF-12; RNF-01/04/05/06 |
| ER y diccionario de persistencia | [02_DATOS.md](02_DATOS.md) | RF-01/08/09/11/12; RNF-01/06 |
| DDL PostgreSQL inicial vigente | [schema_propuesto.sql](schema_propuesto.sql) | Cinco tablas; inicialización nueva y migraciones de ampliación verificadas en PostgreSQL local |
| Contrato REST con ejemplos y errores | [03_API.md](03_API.md) | RF-01 a RF-12; RNF-04 |
| Mockups, carpetas y trazabilidad/pruebas | [04_INTERFAZ_Y_VERIFICACION.md](04_INTERFAZ_Y_VERIFICACION.md) | RF-01 a RF-12; RNF-01 a RNF-06 |

Las propuestas de reglas siguen identificadas en [DECISIONES_PENDIENTES.md](../DECISIONES_PENDIENTES.md). Se puede diseñar con perfiles sintéticos; no se afirma que estos reconozcan archivos reales sin evidencia de sus estructuras/catálogos. Las reglas configurables son archivos versionados del backend, sin interfaz de administración nueva.

Decisiones técnicas: tres contenedores, procesamiento síncrono para volumen objetivo, cuatro tablas, almacenamiento temporal privado y resultados persistidos por lote. Sin colas, servicios adicionales, login, edición de facturas ni deduplicación automática. Los diagramas de esta carpeta sustituyen la propuesta funcional histórica para el nuevo diseño, conservando los originales.

## Diagramas visuales y fuentes editables

| Diagrama | Visual | Fuente |
|---|---|---|
| Arquitectura | [SVG](diagramas/arquitectura.svg) | [Mermaid](diagramas/arquitectura.mmd) |
| To-Be v2 | [SVG](diagramas/to_be_v2.svg) | [Mermaid](diagramas/to_be_v2.mmd) |
| Casos de uso | [SVG](diagramas/casos_de_uso.svg) | [Mermaid](diagramas/casos_de_uso.mmd) |
| Secuencia de procesamiento | [SVG](diagramas/secuencia_procesamiento.svg) | [Mermaid](diagramas/secuencia_procesamiento.mmd) |
| Secuencia de exportación | [SVG](diagramas/secuencia_exportacion.svg) | [Mermaid](diagramas/secuencia_exportacion.mmd) |
| Dominio | [SVG](diagramas/dominio.svg) | [Mermaid](diagramas/dominio.mmd) |
| Entidad-relación vigente | [SVG](diagramas/entidad_relacion.svg) / [PNG](diagramas/entidad_relacion.png) | [Mermaid](diagramas/entidad_relacion.mmd) |

Los SVG son resultados generados. Si se cambia un diagrama, actualizar su bloque en el documento, sincronizar `.mmd` y volver a generar solo los SVG afectados con Mermaid CLI. Estos archivos no sustituyen los PNG históricos.

## Verificación ejecutada y límites

Las 18 filas RF/RNF coinciden exactamente entre Word y Markdown; enlaces locales, tablas Markdown, JSON de ejemplo y cobertura de 18 requisitos comprobados mediante script sin dependencias. Los siete diagramas se renderizaron correctamente con Mermaid CLI 12.0.0 y se comprobó que los SVG son XML válido. La primera renderización detectó un separador reservado en una secuencia; se corrigió y los diagramas restantes pasaron. Las fuentes `.mmd` están sincronizadas con los bloques de documentos.

Las pruebas funcionales de las matrices son futuras. El DDL no se ejecutó ni se validó con parser PostgreSQL: no hay servidor/parser disponible confirmado en esta entrega. Los requisitos, PROMPT, Word, reglas históricas y diagramas originales se conservaron; se comprobó su huella SHA-256 durante el cierre documental.

Próximo paso recomendado: revisar las propuestas de P-01/P-06/P-07 con ejemplos anonimizados y, en una etapa posterior, implementar Fase 2.1 (base Compose/API/frontend/DB). Esta entrega se detiene en Fase 1.
