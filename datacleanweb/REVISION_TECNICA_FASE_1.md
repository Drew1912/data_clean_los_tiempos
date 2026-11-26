# Revisión técnica de Fase 1 — Editorial Los Tiempos

**Fecha:** 17 de noviembre de 2026  
**Material:** `fase_1.zip` (raíz con `01_DISENO.md`, `02_DATOS.md`, `03_API.md`, `04_INTERFAZ_Y_VERIFICACION.md`, `README.md`, `DECISIONES_PENDIENTES.md`, `schema_propuesto.sql` y siete pares de diagramas `.mmd`/`.svg` en `/diagramas`).  
**Dictamen:** **Aprobación condicionada** para iniciar *infraestructura y prueba de concepto con datos sintéticos*; **no** para declarar terminado el diseño de perfiles reales ni desplegar con datos empresariales.

## 1. Aspectos bien resueltos

- Separación frontend Next.js/React, API Flask, motor de datos Python/Pandas, persistencia PostgreSQL y orquestación Docker Compose; sin microservicios adicionales.
- Alcance acotado a carga Excel/CSV, limpieza, clasificación por `C o P` y `CAJA`, consolidación y exportación. Conciliación Ventas–Contabilidad, SAC, facturación electrónica y RBAC fuera de MVP.
- Tres actores conceptuales (Cajas, Contabilidad, Sistemas) y seis casos de uso trazados hacia RF-01…RF-12.
- Preservación de originales, NIT/CI y número de factura como texto, importes exactos (`Decimal`), fechas por perfil, trazabilidad por archivo/hoja/fila.
- Cuatro entidades suficientes para una primera versión (`lote`, `archivo`, `registro`, `observacion`), con claves externas y sin deduplicación destructiva.
- API definida con resultados, errores, paginación, archivos de exportación y estados de lote. Pruebas diseñadas pero no ejecutadas, indicado con transparencia.

## 2. Correcciones necesarias antes de procesar datos reales

| ID | Prioridad | Hallazgo comprobado | Acción concreta |
|---|---|---|---|
| C-01 | **Crítica** | En `01_DISENO.md`, perfiles de ejemplo como `demo_cabecera_xlsx_f4` y el CSV son **sintéticos**. Aún no hay mapeo validado de los archivos reales; las muestras del proyecto incluyen encabezados como `NRO FACTURA`, `FCH. FACTURA`, `NIT/CI`, `MONTO NUMERAL`, `CAJA` y variantes de `C o P`. | Crear 1 perfil Excel y 1 CSV basados en muestras reales anonimizadas. Definir hoja, fila de encabezado, alias exactos (incluidas tildes/variantes), delimitador, fechas DD/MM/AAAA y numéricos. Probar su lectura antes del sistema completo. |
| C-02 | **Crítica** | `DECISIONES_PENDIENTES.md` declara catálogo CAJA parcial. La expresión `^[0-9]+[CLS]$` no garantiza que un código exista; ejemplos `1L`, `1S` son sintéticos. | Confirmar códigos admitidos y su posición de letra por fuente. Aplicar patrón **y** catálogo; códigos desconocidos quedan observados. |
| C-03 | **Alta** | `01_DISENO.md` propone posible duplicado por `(caja_codigo, numero_factura, fecha_factura)` si no hay CUF verificable, y excluir provisionalmente **todos** los candidatos del Excel limpio. Podría retirar facturas legítimas del resultado. | Definir cuándo un duplicado es exacto versus candidato. Añadir casos de misma factura en fuentes diferentes, factura con líneas detalle y numeración reutilizada. Definir con Contabilidad si candidatos permanecen en salida marcados o pasan a observaciones. Nunca borrar entradas. |
| C-04 | **Alta** | El alcance reconoce hojas de **cabecera** y **detalle**, pero excluye detalle. El ejemplo de resultado final del proyecto incluye muchas columnas que deben conservarse. | Aprobar lista de columnas de salida mínima y complementarias. Test de exportación verificando presencia de CUF, ANULADO, CAJA, C/P y columnas originales relevantes, sin fusionar detalle ni perder ceros. |
| C-05 | **Alta** | `to_be_v2.mmd` es un **flowchart Mermaid**, no un BPMN 2.0 importable en Camunda. `casos_de_uso.mmd` también es una representación Mermaid con elipses, no notación UML formal. | Mantener Mermaid para discusión, pero generar To-Be v2 `.bpmn` con pools/lanes, eventos, tareas y compuertas validables en Camunda. Si los profesores piden UML, producir casos de uso en PlantUML/Draw.io. |
| C-06 | **Media** | `schema_propuesto.sql` tiene estructuras y constraints plausibles, pero no fue ejecutado ni validado con un servidor de PostgreSQL. | Ejecutar migración en PostgreSQL de Docker Compose; probar inserciones, restricciones, FK compuesta de observación, origen único, consultas de filtrado y borrado en cascada. |
| C-07 | **Media** | `01_DISENO.md` propone retención 24h y purga automática, más reanudación de estados, control de expiración, hashes y perfiles complejos. Para 10 jornadas esto suma trabajo operativo y puede borrar evidencia de una demostración académica. | Mantener almacenamiento local privado; simplificar purga a limpieza explícita o configurable hasta contar con flujo principal estable. Si se conserva TTL, informar/exportar evidencia antes de expirar. No usar datos sensibles reales sin política autorizada. |
| C-08 | **Media** | El ZIP por sí solo no contiene `LINEA_BASE_MVP.md`, `REQUSITOS.md`, `diagrama_as_is.png` ni `diagrama_to_be.png`, aunque `01_DISENO.md` los enlaza al directorio padre. Los enlaces pueden ser válidos en el repositorio de Codex. | Entregar Fase 1 dentro de la estructura real del repositorio (`docs/fase_1/`) o incluir referencias completas al empaquetar el ZIP. |
| C-09 | **Media** | Tres actores no significan permisos efectivos: `03_API.md` confirma que no hay autenticación. La API devolverá datos financieros en entorno local. | Documentar límite estricto: prototipo local/controlado con datos sintéticos o anonimizados. **No** publicarlo en Internet ni en una red multiusuario hasta definir controles de acceso. |

## 3. Revisión puntual de los documentos

| Documento/diagramas | Juicio | Observación |
|---|---|---|
| `01_DISENO.md`; `arquitectura.mmd`, `dominio.mmd`, secuencias | **Conservar** | Responsabilidades modulares y flujo razonable. Revisar C-03/C-05 antes de formalizar UML/BPMN. |
| `02_DATOS.md`, `entidad_relacion.mmd` | **Conservar con validación** | Modelo mínimo válido como propuesta; conservación de JSON original y trazabilidad útiles. Confirmar granularidad de cabeceras. |
| `schema_propuesto.sql` | **Propuesta, no aprobada técnicamente** | Requiere ejecución real y pruebas de constraints. |
| `03_API.md` | **Conservar** | Estados de lote, filtros AND, reportes y errores bien detallados. Probar contratos con clientes y perfiles reales. |
| `04_INTERFAZ_Y_VERIFICACION.md` | **Conservar** | Mockups y matriz 12 RF + 6 RNF completos. Incorporar prueba de salida de columnas reales. |
| `to_be_v2.mmd`, `casos_de_uso.mmd` | **Rehacer formato si se entrega formalmente** | Son diagramas Mermaid conceptuales, no BPMN XML ni UML estándar de herramienta de modelado. |
| `README.md`, `DECISIONES_PENDIENTES.md` | **Actualizar** | Enlaces fuera del ZIP y pendientes críticos aún abiertos. |

## 4. Decisión de pase a Fase 2

- **Se puede comenzar ya:** Fase 2.1 infraestructura mínima con Compose (Next.js, Flask, PostgreSQL), `GET /health`, una pantalla básica y comunicación frontend–API, más una importación simple con **un perfil sintético** y pruebas.
- **No comenzar aún como implementación definitiva:** deduplicación, reglas empresariales CAJA, interpretación de CUF/ANULADO y perfiles reales hasta confirmar datos y política.
- **No declarar terminado:** ningún RF/RNF antes de pruebas de extremo a extremo ni RNF de seguridad/rendimiento sin mediciones.

### Orden recomendado

1. Cerrar/registrar C-01, C-02 y C-03; identificar dos archivos anonimizados representativos; actualizar perfil de datos y estado de decisiones.
2. Crear `.bpmn` To-Be v2 y, si es exigido, UML casos de uso formal. Conservar archivo Mermaid como antecedente, no sustituir As-Is.
3. Ejecutar prueba vertical mínima: subir un Excel/CSV, normalizar, clasificar, filtrar y exportar una hoja realista, preservando origen.
4. Levantar los tres servicios Docker y probar DDL, API, endpoints y exportación.
5. Implementar observaciones, duplicados **según regla aprobada**, carga múltiple y pruebas de regresión.
6. Ejecutar T01–T12 y N01–N06, medir tiempos y documentar resultados/limitaciones.

## 5. Nota de alcance de esta revisión

Se inspeccionaron todos los Markdown, el SQL y las fuentes de siete diagramas; se comprobaron nombres de archivo y referencias relativas dentro del ZIP. Los SVG están presentes. No se ejecutó la API, Docker Compose ni PostgreSQL: el ZIP contiene diseño, no aplicación. La validez de datos reales y rendimiento permanecen sin verificar. Los archivos y reglas citados fuera del ZIP podrían existir en el repositorio original de Codex.
