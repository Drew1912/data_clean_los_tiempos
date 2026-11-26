# Revisión de la actividad práctica de cierre

> **2026-11-24, usuarios y roles:** [Entrega vigente](USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **Actualización 2026-11-24:** [Auditoría implementada](AUDITORIA.md): historial persistente de accesos y operaciones, permiso de consulta comprobado en Flask y nueva página en el menú. Migración 005; el modelo vigente tiene 6 tablas y 68 atributos. Las referencias anteriores a ausencia de historial o cinco tablas describen entregas previas.


> **Cambio de alcance posterior:** [el responsable sustituye clasificación por contrato y retira departamento](MODALIDAD_CONTRATO.md). RF-04/06 se explican como retirados por instrucción expresa, no como funciones completadas. El catálogo departamental deja de ser bloqueo del alcance actual; continúan pendientes benchmark, aceptación humana y Docker.

> **Actualización 2026-11-23:** se implementaron filtros modalidad/departamento en pantalla, Excel limpio completo, reporte de observaciones y resumen de última exportación. Suite actual: 144 pruebas aprobadas y compilación de producción aprobada. [Evidencia y alcance de esta entrega](EXPORTACIONES.md). Las matrices del 2026-11-19 que siguen son el registro histórico anterior; sus pendientes RF-05/06/10/11/12 de interfaz/exportación quedan atendidos por esta actualización. Permanecen pendientes catálogo empresarial, benchmark y validación humana/Docker.

Fecha: 2026-11-19, America/La_Paz. Fuente docente: [ACTI_FINAL.md](../ACTI_FINAL.md). Alcance revisado: prototipo local de carga, limpieza y comparación configurable de facturas, con acceso de administrador único añadido por solicitud expresa del responsable. No se presenta como el MVP completo ni como aceptación empresarial.

## Actividad 1 — Auditoría de funcionalidades

| Función solicitada | Qué existe y cómo demostrarlo | Estado actual |
|---|---|---|
| Inicio de sesión y control de usuarios | admin / admin; hash en PostgreSQL; sesión firmada; API protegida; cierre que revoca sesiones anteriores | Implementado y probado para una cuenta. No hay administración de otros usuarios ni roles |
| Registro de información | Carga de Excel/CSV; persistencia de lote, archivos, registros originales/normalizados y observaciones | Implementado. Es registro mediante importación; no un formulario de alta de facturas |
| Modificación y actualización | Limpieza segura registra cambios sin sobrescribir originales; se pueden cambiar columnas/criterios de comparación | Parcial respecto a una auditoría genérica. No hay edición manual de registros persistidos; cambiar columnas no equivale a editar una factura |
| Eliminación | Comando técnico de limpieza de lotes vencidos con borrado de temporales y cascadas SQL | Existe mantenimiento técnico. No hay botón de borrar facturas individuales. Nueva carga y Cerrar sesión no eliminan datos |
| Búsquedas y consultas | Número de factura como búsqueda; NIT/CI y monto como comparación; referencia, filtros de resultado, paginación, archivo/hoja/fila | Implementado y probado. No garantiza identidad fiscal entre emisores/series |
| Generación de reportes | Resumen de cargados/válidos/observados, matriz de comparación y observaciones en pantalla | Parcial: exportación Excel/reporte descargable pendiente. No confundir una tabla visible con un archivo exportado |
| Conexión y base de datos | PostgreSQL, restricciones, FK, carga/lectura, migraciones y healthcheck | Implementado y probado en instancia local aislada |

La consigna dice **«según corresponda»**. La modificación/eliminación manual de facturas no forman parte del alcance autorizado del prototipo. Si el docente exige CRUD completo, habrá que acordar esa ampliación; no se marca como funcionalidad existente. La exportación Excel sí pertenece al MVP original y sigue siendo un pendiente concreto.

## Actividad 2 — Matriz de pruebas realizadas

| Funcionalidad | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|
| Inicio de sesión | Permitir admin/admin, rechazar credenciales incorrectas | Login válido, credencial incorrecta 401, formulario con error; cookie HttpOnly; sesión conservada al recargar | Correcto para cuenta demo |
| Acceso sin sesión | Bloquear operaciones de datos | API de perfiles/lotes/carga/procesamiento/comparación devuelve 401; interfaz muestra login | Correcto |
| Cierre de sesión | Impedir seguir consultando con la sesión anterior | Logout revoca versión de sesión; reproducción de cookie anterior y acceso anónimo rechazados | Correcto |
| Registro | Guardar los datos importados sin perder origen | CSV ficticio: 5 cargados = 3 válidos + 2 observados; 5 incidencias; ceros e importes conservados | Correcto |
| Modificación | Actualizar datos seleccionados cuando exista una función de edición | No hay edición manual. Se comprobaron normalización segura y cambios de selección de columnas, que son funciones diferentes | Requiere ajustes solo si se exige CRUD manual; no evaluado como aprobado |
| Eliminación | Eliminar mediante una función incluida en alcance | Tests de limpieza de lotes vencidos conservan los no vencidos; no existe eliminación individual en interfaz | Requiere ajustes si se exige eliminación individual; mantenimiento técnico probado |
| Búsqueda/comparación | Localizar por factura aunque NIT/monto difieran | Pruebas de igualdad, diferencia, ausencia, dato incompleto, varias filas, filtros y ceros; los observados pueden participar | Correcto para reglas documentadas |
| Reportes | Presentar información correcta y permitir la salida requerida | Resúmenes, observaciones y comparación visibles; exportaciones no implementadas | Requiere ajustes: descarga Excel pendiente |
| Base de datos | Almacenar/recuperar, aplicar relaciones y conservar datos al migrar | Pruebas de restricciones y autor del lote; migraciones/seed idempotentes; hash de contraseña; lotes conservados | Correcto en entorno probado |
| Mensajes y errores | Orientar ante rechazo o fila no comparable | Aviso distingue filas buscables y no buscables e incluye hoja/fila/motivo; error de formato desconocido no propone un perfil incompatible como solución automática | Correcto en recorrido técnico; comprensión humana pendiente |

**Ejecución de esta revisión:** 132 pruebas pytest aprobadas en 74,67 s; compilación de producción Next.js/TypeScript aprobada. Tras extender el healthcheck a las cinco tablas, se volvieron a ejecutar sus cuatro pruebas: aprobadas. Los tests de API crean esquemas PostgreSQL aleatorios aislados que se retiran al terminar. No se cargaron datos empresariales en las capturas.

**Pruebas HTTP ejecutadas:** página y proxy de salud HTTP 200; script autenticado de carga/limpieza con 5 = 3 + 2 y 5 incidencias, seguido de logout. **Navegador ejecutado:** login incorrecto/correcto, navegación por teclado de usuario a contraseña, cookie inaccesible a document.cookie, sesión al recargar, carga de dos Excel ficticios, comparación, aviso desplegable con fila/motivo, ancho móvil 390 px, logout y consulta posterior 401, sin errores JavaScript.

Las pruebas de navegador se hicieron con Flask en 18000 y Next.js en 13000, usando un esquema temporal separado del de la aplicación; estos no son los puertos normales de arranque. La base instalada para el proyecto sigue en 55439. No se ejecutó Docker ni una validación del sistema en producción.

Al finalizar se detuvieron los dos servidores de pruebas y se retiraron su esquema y copias privadas ficticias. PostgreSQL queda iniciado. La instalación normal ya recibió la migración y la cuenta; para usar la nueva pantalla es necesario iniciar Flask y el frontend compilado según [LOGIN_ADMIN.md](LOGIN_ADMIN.md).

## Actividad 3 — Evaluación de la experiencia del usuario

Esta es la parte 3 de **ACTI_FINAL.md**. Lo siguiente es una inspección técnica y un recorrido de navegador; todavía no es un estudio de usabilidad con personal de Cajas/Contabilidad ni una aprobación del docente.

| Pregunta docente | Respuesta sustentada por la revisión actual | Qué falta para cerrarla |
|---|---|---|
| ¿Es fácil de utilizar? | El recorrido dispone de acceso, carga y selección de columnas sin programar. Comparar ejecuta la limpieza pendiente automáticamente. Se muestran formatos/límites y ejemplos ficticios | Observar a un usuario que no haya recibido instrucciones del desarrollador; registrar ayudas y obstáculos. El arranque local aún necesita apoyo técnico |
| ¿Los botones, menús y opciones son comprensibles? | Acciones nombradas Ingresar, Cargar archivos, Buscar facturas y comparar, Limpiar y revisar registros, Nueva carga y Cerrar sesión. Selectores distinguen factura, NIT/CI y monto | Confirmar que se comprende referencia, no disponible, datos incompletos y varias filas; Nueva carga no debe interpretarse como borrar datos |
| ¿La información está organizada y es legible? | Secciones 01 Importación, 02 Comparación, 03 Revisión. Estados por archivo, filtros/paginación y detalles de hoja/fila reducen la información que hay que leer a la vez | Revisar tablas con muchos archivos, zoom del navegador y tamaño de textos secundarios con usuarios; tablas amplias usan desplazamiento interno |
| ¿Los mensajes de error orientan? | Credenciales incorrectas, error de conexión y rechazo estructural tienen mensajes. El aviso de filas sin número ahora muestra cuántas sí se buscaron y permite ver ubicación/motivo | Validar comprensión con un usuario. Seguir afinando mensajes de importes ambiguos, fechas, campos ausentes y sesión/CSRF; no basta con que aparezcan en pantalla |
| ¿La navegación entre pantallas es sencilla? | Login → área de trabajo → logout. Las pestañas de registros/observaciones y los filtros permiten revisar el mismo lote sin navegar a otras páginas | No existe historial ni recuperación del lote en pantalla tras recargar/cerrar sesión. La sesión se conserva, pero el estado de trabajo de la pantalla no |
| ¿Mantiene uniformidad visual? | Login y área de trabajo comparten marca, azul, fondo claro, paneles, tipografías y botones. Probados escritorio y móvil sin desbordamiento global | Auditoría completa de accesibilidad: contraste, lector de pantalla, zoom 200 % y recorrido completo por teclado. La prueba actual cubre pasos concretos, no certifica WCAG |

### Mejoras realizadas y demostrables

1. Acceso con una cuenta y cierre de sesión, con mensajes de credencial incorrecta, contraseña oculta y opción de mostrarla.
2. Controles deshabilitados durante operaciones y mensajes de estado que indican carga/procesamiento/comparación.
3. Selección explícita de columnas y archivo de referencia; opción No disponible sin inventar columnas ausentes.
4. Acción de comparar que ejecuta la limpieza necesaria sin exigir un paso previo adicional.
5. Vista por factura/archivo que distingue coincidencia, diferencia, ausencia, incompleto y varias filas; valores y origen desplegables.
6. Conservación visible de observados y detalle; filtro de todos/válidos/observados para evitar que «no se ve nada» oculte filas importadas.
7. Aviso de filas sin factura utilizable corregido: incluye número de filas que sí pudieron buscarse, columna aplicada y lista de hoja/fila/motivo. No presenta el archivo completo como fallido.
8. Perfiles de las estructuras de material y febrero, con cabeceras por hoja y tratamiento de dimensiones de estilo; formato desconocido y formato ambiguo tienen mensajes distintos.
9. Etiquetas de formulario y foco visible; recorrido inicial con teclado y revisión de viewport móvil.

Estas mejoras proceden de iteraciones del prototipo; no todas fueron introducidas en la revisión del login. El acceso y el aviso detallado son mejoras de esta entrega.

### Aspectos pendientes y prueba con usuarios propuesta

| Tarea a observar | Criterio propuesto | Evidencia a completar por el grupo |
|---|---|---|
| Ingresar y corregir una contraseña errónea | Identifica el error y logra entrar | Participante, fecha, dificultad y ayuda recibida |
| Cargar dos Excel de formatos admitidos | Distingue admitidos/rechazados y continúa | Captura con datos ficticios y comentario del participante |
| Elegir factura/NIT/monto y referencia | Explica qué se busca y qué se compara | Selección realizada y explicación en sus palabras |
| Localizar una diferencia y una ausencia | Identifica el archivo y hoja/fila correctos | Resultado observado y tiempo medido, sin inventarlo |
| Interpretar una fila sin número y una factura repetida | Comprende que hay filas conservadas que requieren revisión | Respuesta del usuario y mejora sugerida |
| Cerrar sesión | Sale y no vuelve a consultar sin ingresar | Evidencia del cierre |

Participantes y resultados humanos: **pendientes**. No se asignan porcentajes, tiempos, satisfacción ni aceptación sin ejecutar esa prueba. Producto de la actividad 3 disponible: listado de mejoras realizadas, pendientes concretos, capturas y ficha de validación propuesta.

## Actividad 4 — Documentación técnica

| Elemento | Documento/recurso disponible | Verificación |
|---|---|---|
| Manual de usuario | [MANUAL_USUARIO.md](MANUAL_USUARIO.md) | Sí, versión actual del prototipo; revisión con usuarios pendiente |
| Manual técnico | [MANUAL_TECNICO.md](MANUAL_TECNICO.md), diseño de Fase 1 y contratos | Sí; distingue diseño histórico de implementación actual |
| Base de datos | [Diccionario/DER](fase_1/02_DATOS.md), [SVG actualizado](fase_1/diagramas/entidad_relacion.svg), DDL y migraciones 002/003 | Sí: cinco tablas actuales; DER extendido con usuario y autor del lote |
| Código fuente | frontend/, backend/, tools/, pruebas separadas | Sí en el proyecto local; preparar la copia final excluyendo temporales/credenciales/datos empresariales |
| Instalación | [INICIAR_SERVICIOS.md](INICIAR_SERVICIOS.md), Compose y [LOGIN_ADMIN.md](LOGIN_ADMIN.md) | Sí para local probado; ejecución Docker pendiente |
| Credenciales | [LOGIN_ADMIN.md](LOGIN_ADMIN.md): cuenta demo admin/admin | Sí: demostración controlada; no contiene claves personales ni clave de firma real |

## Actividad 5 — Guion de simulacro (preparado, no ejecutado)

1. **Problema:** archivos de facturación con hojas/cabeceras distintas dificultan localizar inconsistencias y ausencias sin perder su origen.
2. **Solución:** prototipo web que importa y normaliza con reglas explícitas, conserva originales y compara por factura los campos seleccionados.
3. **Funciones:** mostrar acceso, carga múltiple, columnas/referencia, comparación y observaciones. Aclarar la falta de exportación final.
4. **Tecnología:** Next.js para interfaz/proxy, Flask para API y reglas, PostgreSQL para trazabilidad, openpyxl/xlrd/CSV para lectura y Decimal para montos; Docker Compose preparado.
5. **Demostración de 5–7 minutos propuesta:** ingresar; cargar dos archivos ficticios; seleccionar columnas; comparar; mostrar una coincidencia/diferencia/ausencia del juego de prueba; abrir origen y aviso; cerrar sesión. Preparar previamente esos casos y probarlos antes de exponer.
6. **Resultados:** mostrar conteos reproducibles, pruebas y capturas; no presentar las pruebas como aceptación de la empresa.
7. **Dificultades:** .xls/.xlsx, cabeceras en distintas filas, estilos que inflan dimensiones, columnas ausentes, ceros, importes ambiguos y repeticiones de factura.
8. **Siguiente versión:** exportación Excel y observaciones, filtros modalidad/departamento en interfaz, catálogo validado, recuperación de lotes y validación con usuarios.

Debe realizarlo el grupo: repartir la exposición, cronometrar, comprobar que todos explican el sistema y registrar preguntas/ajustes. No se afirma que el simulacro ya ocurrió.

## Pendientes principales del sistema completo

- RF-10/11: Excel final y reporte descargable; la vista de observaciones no completa por sí sola la exportación exigida.
- RF-05/06: filtros modalidad/departamento existen en consultas API, pero faltan sus controles completos en interfaz.
- RF-03/04/09: clasificación/unificación tienen implementación limitada a perfiles/catálogos documentados; validar catálogos empresariales y aceptación del consolidado. No inferir cajas o modalidades por nombres de archivos.
- RF-12: resumen cargados/válidos/observados funciona; exportados permanece en 0 al no existir exportación.
- RNF-02: medir el caso acordado de 1.000 registros por fuente en equipo documentado; la duración de pytest no es un benchmark de procesamiento.
- RNF-03/06: validación con usuarios y condiciones de despliegue/acceso/retención definitivas. El login demo no equivale a seguridad de producción.

Prioridad de cierre propuesta: completar exportaciones y filtros previstos; ejecutar prueba con usuarios de la actividad 3; medir rendimiento; verificar instalación Docker en equipo disponible; realizar el simulacro. Edición/eliminación manual solo si se acuerdan como requisitos adicionales.

## Evidencias

- [Login](evidencias_cierre/login.png).
- [Comparación y aviso con datos ficticios](evidencias_cierre/comparacion.png).
- [Vista móvil](evidencias_cierre/movil.png).
- `backend/tests/test_auth.py`, `test_comparison.py`, `test_upload_api.py`, `test_febrero_formats.py`, `test_schema.py`, `test_health.py` y resto de la suite.
- Reproducir pruebas y comandos: [manual técnico](MANUAL_TECNICO.md). Las capturas son evidencia técnica; no sustituyen las respuestas de usuarios reales.

## Evidencia ejecutada — 2026-11-24

- PostgreSQL 17: migración 005 ejecutada, repetición sin pérdida de datos ni restitución de permisos revocados.
- Suite completa del backend: **173 pruebas aprobadas en 161,61 s**, con esquemas PostgreSQL aislados; incluye 16 casos de auditoría.
- Frontend compilado en directorio de prueba separado y servido con Next.js; Chromium comprobó acceso admin, cuatro enlaces del menú, consulta real, filtro por acción, cierre de sesión y rechazo 401 posterior. Capturas [escritorio](evidencias_cierre/auditoria_desktop.png) y [móvil](evidencias_cierre/auditoria_movil.png), sin desborde a 390 px.
- No se ejecutó Docker Compose en esta entrega. Gestión de múltiples cuentas, política de retención de auditoría, recuperación de respaldos y despliegue de producción siguen pendientes; no se presentan como funciones probadas.
