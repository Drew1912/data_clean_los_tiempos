# Interfaz, organización y verificación

> **2026-11-24:** [Historial de auditoría](../AUDITORIA.md) implementado con acceso por permiso; seis tablas/68 atributos. GET `/api/v1/auditoria` devuelve eventos paginados; la respuesta de sesión incluye `usuario.puede_ver_auditoria`. Se conservan contratos operativos anteriores.


> **RNF-03 — navegación 2026-11-23:** tres páginas con menú lateral, etapa activa y estados vacíos orientativos. Layout persistente conserva el trabajo al cambiar rutas; foco en título y menú adaptado a móvil. Recorrido de navegador y compilación verificados, con descarga y sesión; la aceptación humana sigue pendiente. [Manual y capturas](../MANUAL_USUARIO.md#navegación-por-páginas).

> **Última regla de modalidad:** [contrato seleccionado por archivo, C/P inicial y departamento retirado](../MODALIDAD_CONTRATO.md). RF-03 se modifica por instrucción expresa y RF-04/06 se retiran del alcance operativo, sin presentarlos como completados. 157 pruebas aprobadas, migración 004 y navegador con Excel descargado verificados. Las matrices originales permanecen como línea base histórica.

> **2026-11-23 — RF-05/06/10/11/12:** filtros AND en interfaz y API, exportación completa sin paginación, reporte de todo el lote y metadatos de última generación implementados. `test_exportation.py` y recorrido de navegador con reapertura de archivos descargados verifican filtros, cero filas, precisión, fórmulas literales, repeticiones y fallos sin alterar contadores. [Resultado de 144 pruebas y evidencia](../EXPORTACIONES.md). Catálogos empresariales, benchmark y prueba humana siguen pendientes.

> **Cierre académico 2026-11-19:** actividad 1 amplía el acceso con administrador único; actividad 3 recibe evaluación técnica y evidencias, con prueba humana pendiente. Login/API protegida, migración/DER y mejora del aviso de filas sin clave se verifican con test_auth.py, test_comparison.py y recorrido de navegador. No se presenta autenticación como un RF original ni se marca el MVP completo. [Matriz y resultados actuales](../REVISION_ACTIVIDAD_FINAL.md).

> **Corrección de lectura 2026-11-19:** RF-01/02/07/08 y RNF-01/04 se contrastan también con los nueve Excel de febrero indicados por el usuario. Evidencia: `test_febrero_formats.py` (cabeceras por hoja, dimensión formateada excesiva, columnas complementarias repetidas, falta de NIT, detalle, carga y comparación) y prueba aislada de los nueve originales con 1.444 filas conservadas. [Estructuras y resultados ejecutados](../FORMATOS_FEBRERO.md). No se alteran requisitos fuente ni esquema SQL.

> **Trazabilidad adicional 2026-11-19:** la instrucción reciente de comparación configurable se implementa sobre RF-01/02 (carga y columnas), RF-07 (normalización segura), RF-08 (señalar ambigüedad sin excluir), RF-09 (origen conservado) y RNF-03/04 (usabilidad y manejo de errores). Es una ampliación explícita del usuario, no una reinterpretación silenciosa de los RF. Artefactos: `ComparisonWorkspace.tsx`, `services/comparison.py`, `POST /lotes/{id}/comparaciones`, `test_comparison.py`. El esquema SQL y las funciones de clasificación no cambian. [Flujo, estados y evidencia](../COMPARACION_FACTURAS.md).

> Matriz de diseño histórico. La evidencia y el estado actual de carga/limpieza están en [Fase 2.2/2.3](../fase_2_2_3/README.md). T01/T02/T07 y parte de T08 ya tienen implementación y pruebas con perfiles de demostración; las exportaciones siguen propuestas.

## Mockups de pantallas principales

Wireframes de baja fidelidad, sin frontend implementado. Una página de trabajo con secciones y pestañas, sin dashboards ni selector de rol. Los perfiles muestran si son sintéticos y sus convenciones de lectura; los mensajes usan lenguaje administrativo.

### Carga y estado de fuentes — RF-01/02; RNF-03/04

```text
Limpieza de facturación
1. Cargar archivos    2. Procesar    3. Revisar y descargar

[Elegir archivos Excel/CSV]
Archivo           Formato de lectura                  Estado
cabeceras.xlsx    [Cabecera Excel · fila 4 v]          Admitido
facturas.csv      [Cabecera CSV · UTF-8 · ; v]         Admitido
detalle.xlsx      [Detalle Excel v]                    Fuera del consolidado

Formato elegido: cabecera en fila 4 · hoja Facturas
CSV: UTF-8, separador ;, decimal coma (según perfil elegido)
[Cargar]   [Procesar cabeceras admitidas]

Se admitieron 2 de 3 archivos. El detalle no se mezclará con facturas.
[Consultar motivos]  [Descargar observaciones de carga]
```

El selector de perfil existe por archivo; no inferir por nombre. Al subir mostrar límite configurado y estado, errores junto al archivo, opción de nueva carga que crea otro lote. Mientras se procesa, deshabilitar el botón y mostrar «Procesando…», sin porcentaje inventado ni éxito anticipado. Si se pierde conexión, consultar el lote antes de repetir.

### Resumen, filtros y resultados — RF-03 a RF-10/12

```text
Lote completado · 2 archivos admitidos · 0 rechazados
Cargados 9   Válidos 6   Observados 3
Exportados en el último archivo: 0 · Sin exportación todavía

Modalidad [Contado v]    Departamento [Cochabamba v]    [Aplicar filtros]
Seleccionados: 1 cabecera válida

[Registros válidos]  [Observaciones (3)]  [Archivos y advertencias]
Factura  Fecha        NIT/CI       Monto   Modalidad Departamento Origen
000101   2026-10-15   00012345001  151.89  Contado   Cochabamba   demo.csv:2
                                                   CAJA: 1C
[Anterior]  Página 1 de 1  [Siguiente]

[Descargar Excel de 1 registro]  [Descargar observaciones del lote]
Último archivo: cantidad, fecha y filtros usados (cuando exista)
```

La vista usa AND y solo cabeceras válidas. Los detalles no se contabilizan como cabeceras observadas; su exclusión se explica por archivo/hoja. Cambiar filtro no recalcula clasificaciones ni vuelve a procesar. «Todos» no incluye observados en el Excel limpio.

Si no hay coincidencias: «No hay registros válidos con estos filtros»; permitir Excel con encabezados y cero filas. Si no hubo cabeceras admitidas, no mostrar «lote completado» ni habilitar procesamiento. Antes de completar, resultados con guion/pendiente en vez de ceros ficticios.

### Observaciones e incidencias — RF-08/11; RNF-04

```text
Observaciones del lote: 4 incidencias en 3 cabeceras
Archivo     Hoja      Fila  Campo      Motivo
demo.csv    —         8     Fecha      Fecha imposible: 2026-02-30
demo.csv    —         9     C o P      Modalidad no reconocida
demo.xlsx   Facturas  12    —          Fila vacía interior
demo.csv    —         9     Factura    Posible duplicado · grupo demo-1

[Ver contexto original de una incidencia]
Archivo/hoja/fila · valor original · regla aplicada
[Descargar reporte completo de observaciones]

Advertencias: CUF sin validador confirmado · ANULADO conservado sin interpretar
```

La tabla anterior ilustra columnas, no el fixture de nueve filas; la leyenda de cantidades debe derivarse de las filas reales. En un caso con dos incidencias en una misma cabecera, mostrar ambas sin contar dos veces esa cabecera. Incidencia de archivo puede tener hoja/fila/campo ausentes; representar «no aplica». Valores largos se truncan visualmente con expansión accesible. No exponer ruta absoluta, credenciales ni stack.

Accesibilidad mínima propuesta: etiquetas para controles, navegación por teclado, foco visible, estado anunciado al completar, mensajes que no dependan solo del color y tablas con encabezados. Para RNF-03 registrar un recorrido con usuario funcional, sin conocimientos de programación.

## Estructura modular propuesta

Solo `docs/fase_1/` y los documentos indicados existen por esta entrega. El resto es árbol objetivo de Fase 2, no archivos creados ni comandos ya ejecutables.

```text
datacleanweb/
  PROMPT.md
  .env.example
  .gitignore
  compose.yaml
  frontend/
    Dockerfile
    package.json
    src/
      app/
        page.tsx
        api/v1/[...path]/route.ts       # proxy interno hacia Flask
      components/
        CargaArchivos.tsx
        Filtros.tsx
        Resumen.tsx
        TablaResultados.tsx
        TablaObservaciones.tsx
      lib/api.ts
      types/facturacion.ts
    tests/flujo-principal.*             # herramienta a elegir al implementar
  backend/
    Dockerfile
    requirements.txt
    app/
      __init__.py                      # factory Flask
      config.py
      routes/
        health.py
        perfiles.py
        lotes.py
        resultados.py
        exportaciones.py
      validators/peticiones.py
      services/
        importacion.py
        limpieza.py
        validacion.py
        clasificacion.py
        duplicados.py
        consolidacion.py
        exportacion.py
        resumen.py
        temporales.py
      readers/
        excel.py
        csv.py
      profiles/                        # JSON versionados, sin datos reales
      repositories/lotes.py            # SQL parametrizado/transacciones
      domain/tipos.py
    db/001_inicial.sql                 # derivará del DDL de diseño revisado
    tests/
      fixtures/                        # solo sintéticos
      test_importacion.py
      test_reglas.py
      test_clasificacion.py
      test_duplicados.py
      test_consolidacion.py
      test_api.py
      test_exportacion.py
      test_rendimiento.py
  docs/
    REQUSITOS.md                       # conservar línea base actual
    LINEA_BASE_MVP.md
    DECISIONES_PENDIENTES.md
    FASE_0_REVISION_Y_ALINEACION.md
    fase_1/
      README.md
      01_DISENO.md
      02_DATOS.md
      schema_propuesto.sql
      03_API.md
      04_INTERFAZ_Y_VERIFICACION.md
```

Los volúmenes de Compose, no una carpeta pública frontend, contienen archivos administrativos. Logs técnicos solo identifican solicitud, etapa y código. No se crean repositorios adicionales ni carpeta React distinta de Next.js.

## Matriz RF → actores/CU → componentes → contrato → pruebas

T01–T12 continúan los identificadores de Fase 0; los casos nuevos amplían su alcance conforme a decisiones del usuario. Estado de todas las pruebas funcionales: **no ejecutadas**, sin aplicación implementada.

| RF | Actor / CU | Componentes | API | Prueba y aceptación |
|---|---|---|---|---|
| RF-01 | Cajas / CU-01 | CargaArchivos, importacion, readers | POST /lotes | T01: varios .xlsx/.csv, nombres repetidos; cabeceras fila 1/4, hojas múltiples y línea física CSV; cada origen inequívoco |
| RF-02 | Cajas / CU-01 | profiles, validators, readers | GET /perfiles; POST /lotes | T02: alias explícitos; columnas ausentes/colisiones/perfil desconocido rechazados sin adivinar |
| RF-03 | Contabilidad / CU-02 | clasificacion | POST /lotes/{id}/procesamiento | T03: C/P→Contado/Crédito; X y vacío observados; nombre de archivo no interviene |
| RF-04 | Contabilidad / CU-02 | clasificacion, profiles | POST /lotes/{id}/procesamiento | T04: 0C/1C y 1L/1S sintéticos; 9C aunque coincida regex es desconocido si no está en catálogo; CL01 inválido; preservar código completo |
| RF-05 | Cajas / CU-03 | Filtros, consultas | GET /registros y /resumen bajo lote | T05: contado/credito/todos; seleccionados exactos; solo válidos |
| RF-06 | Cajas / CU-03 | Filtros, consultas | GET /registros y /resumen bajo lote | T06: matriz 3×4 de filtros con AND, no OR; selección vacía válida |
| RF-07 | Contabilidad / CU-02 | limpieza, validacion, domain | POST /procesamiento bajo lote | T07: ceros, CI con complemento conservado, fechas ISO/imposibles/ambiguas, 151.89/333,60/2.680,00/1,234; Decimal exacto y origen intacto |
| RF-08 | Contabilidad / CU-02; Sistemas / CU-06 | validacion, duplicados | POST /procesamiento; GET /observaciones | T08: vacíos interiores/faltantes; CUF válido repetido; respaldo sin CUF; copia con/sin CUF; CUF distintos; ninguna eliminación; detalles no mezclados |
| RF-09 | Contabilidad / CU-02 | consolidacion, repositories | POST /procesamiento; GET /registros | T09: estructura uniforme, originales/traza; candidato válido permanece marcado en salida y observaciones; misma factura en dos productos no fusionada |
| RF-10 | Contabilidad / CU-05 | exportacion, proxy, interfaz | POST /exportaciones/limpios | T10: reabrir XLSX; T10-C04: CUF/ANULADO/CAJA/C-P, adicionales, ceros/precisión; textos con prefijo de fórmula sin ejecución; toda selección sin limitarse a página; adicionales/CUF/ANULADO conservados |
| RF-11 | Contabilidad, Sistemas / CU-06 | TablaObservaciones, exportacion | GET /observaciones; POST /exportaciones/observaciones | T11: reporte separado con origen/campo/motivo, incidencias de archivo sin fila, candidatos relacionados; no ocultar incidencias al filtrar limpios |
| RF-12 | Contabilidad / CU-04 | Resumen, resumen, repositorio | GET /resumen; POST /exportaciones/limpios | T12: fixture 9=6+3, filtro selecciona 1; varias incidencias por fila; exportados tras éxito, fallo y descarga repetida sin acumulación |

Las rutas abreviadas de la tabla cuelgan de `/api/v1/lotes/{id}` salvo `/lotes` y `/perfiles`. Las responsabilidades conceptuales no limitan endpoints por actor.

## Matriz RNF y aceptación del diseño

| RNF | Verificación prevista | Criterio y evidencia |
|---|---|---|
| RNF-01 | N01: hashes originales antes/después, rutas de salida diferentes | Bytes de entrada intactos, sin sobrescritura |
| RNF-02 | N02: dos fuentes de 1.000 cabeceras, medir lectura→resultados/reportes; tres ejecuciones | Propuesta conservadora: cada lote <30 s; registrar SO/CPU/RAM, versiones, Docker, tamaño y tiempos. Equipo pendiente; no afirmar rendimiento ahora |
| RNF-03 | N03: recorrido carga→proceso→filtros→descargas y observaciones con usuario | Sin terminal/programación; foco/etiquetas/errores comprensibles; no login ficticio |
| RNF-04 | N04: corruptos, encoding/comillas inválidos, zip excesivo, firma falsa, caídas de DB, expiración y repetición de POST | Error controlado y recarga; sin lectura parcial oculta, doble inserción ni datos sensibles en mensajes |
| RNF-05 | N05: revisión de estructura y pruebas por responsabilidad | Readers, limpieza, clasificación, consolidación, reportes y repositorio separados; sin servicios adicionales |
| RNF-06 | N06: .gitignore/secretos, rutas/nombres, temporales privados, purga y textos de fórmula | No datos reales en repo/logs; expiración comprobada, sin residuos ocultos; API no expuesta fuera del contexto local previsto |

El diseño se considera revisable cuando cada RF/RNF tiene cobertura, actores y flujo respetan la línea base, los contratos distinguen errores/estados y pendientes sensibles son visibles. No equivale a aceptación funcional del software. Los mockups no agregan filtros temporales, administración de perfiles ni edición de registros.

## Fixture actualizado de referencia

Perfil cabecera sintético con seis combinaciones C/P×1C/1L/1S; facturas 000101–000106 y NIT ficticio 00012345001, fecha ISO 2026-10-15, monto 151.89. Añadir factura 000107 con fecha imposible, factura 000108 con C o P=X y fila vacía interior: nueve filas cargadas, seis válidas y tres observadas, filtro contado+cochabamba selecciona una. En CSV la fila vacía explícita interior se conserva; un terminador final no crea registro.

Fixtures separados para duplicados no contaminan el conteo base: dos CUF sintéticos iguales que pasan un validador de demostración (no tributario), dos claves alternativas iguales sin CUF y copia con CUF/sin CUF. Todas las ocurrencias candidatas se conservan con avisos en observaciones y, si no tienen errores bloqueantes, en la salida válida (C-03). Las líneas de detalle se informan fuera del consolidado y de los contadores de cabecera. S01–S26 de Fase 0 se mantienen como catálogo histórico, actualizando cajas y granularidad conforme a esta línea base.

## Verificación documental y límites

Revisión prevista/ejecutable en esta entrega: leer todos los documentos actuales, contrastar nuevamente Word/Markdown, comprobar hashes de fuentes antes/después, referencias locales, tablas y cobertura de 18 requisitos. Para SQL se puede validar sintaxis con parser PostgreSQL si ya está disponible; la ejecución en PostgreSQL queda para Fase 2. Para Mermaid se puede validar con CLI/parser si está disponible; no se instalarán herramientas solo para simular una prueba de producto.

Los resultados reales de esta revisión se registran en README.md. No hay comandos de arranque de la aplicación todavía: entregar `docker compose up` como verificado en esta etapa sería incorrecto.

## Trazabilidad de las correcciones críticas/altas

| Hallazgo | RF afectados | Evidencia/prueba | Estado |
|---|---|---|---|
| C-01 | RF-01/02/07 | test_profiles_reference: CSV/Excel filas 1 y 4; aliases exactos y ceros | Lectura sintética; perfiles empresariales no habilitados |
| C-02 | RF-04/08 | Listas observada/admitida separadas y habilitado=false | Catálogo real pendiente; sin clasificador implementado |
| C-03 | RF-08/09/10/11/12 | T08-C03: exactos, candidatos, numeración reutilizada y detalle; SQL admite copias entre orígenes y avisos sin forzar estado | Diseño corregido; motor funcional pendiente |
| C-04 | RF-09/10/11 | T10-C04: CUF, ANULADO, CAJA, C/P, adicionales y origen | Contrato actualizado; exportación pendiente |
| C-05 | RF-01 a RF-12 | test_bpmn: XSD OMG, referencias, carriles, conectividad y DI | BPMN formal; sin ejecución de motor/GUI |
| Infraestructura 2.1 | RNF-04/05; base para RF | test_health, test_schema y tools/smoke_connectivity.py | Resultados reales en docs/fase_2_1/README.md |
