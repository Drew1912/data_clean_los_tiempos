# Manual de usuario — DataClean

> **2026-11-24, usuarios y roles:** [Entrega vigente](USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **Actualización 2026-11-24:** [Auditoría implementada](AUDITORIA.md): historial persistente de accesos y operaciones, permiso de consulta comprobado en Flask y nueva página en el menú. Migración 005; el modelo vigente tiene 6 tablas y 68 atributos. Las referencias anteriores a ausencia de historial o cinco tablas describen entregas previas.


## Navegación por páginas

Desde 2026-11-23, el menú lateral separa el trabajo en **Importación** (`/importacion`), **Comparación** (`/comparacion`) y **Revisión** (`/revision`). En móvil el mismo menú aparece como barra superior. La dirección inicial `/` abre Importación.

- **Importación:** seleccionar/cargar archivos, revisar admisión y elegir la columna de contrato. Puedes limpiar y pasar directamente a Revisión o continuar a Comparación.
- **Comparación:** elegir columnas y referencia, ejecutar la búsqueda por factura y revisar coincidencias/diferencias/ausencias. El enlace a Importación permite verificar el contrato antes de procesar.
- **Revisión:** ver resumen, registros y observaciones, filtrar modalidad y descargar los Excel. Si todavía falta procesamiento, permite ejecutarlo desde esta página.

Usa el menú para cambiar de página: conserva archivos elegidos, lote, contratos, resultados de comparación y filtros durante la navegación interna, incluidos Atrás/Adelante. **Nueva carga** limpia el espacio de trabajo de pantalla y vuelve a Importación; no borra lotes persistidos. Abrir Comparación/Revisión sin carga muestra instrucciones para empezar. Recargar completamente o abrir otra pestaña aún no recupera el lote en pantalla; la recuperación de historial sigue pendiente. Cerrar sesión retira el espacio de trabajo.

[Captura de Revisión con menú lateral](evidencias_cierre/navegacion_revision.png) · [Vista móvil](evidencias_cierre/navegacion_movil.png).

## Flujo de uso

Actualización: [Contado/Crédito por contrato](MODALIDAD_CONTRATO.md). Después de cargar y antes de procesar, elige la columna de contrato por archivo. P inicial = Crédito; C inicial = Contado. El departamento ya no se usa en pantalla ni se exige para considerar una factura válida; las indicaciones de filtros departamentales siguientes corresponden a la entrega previa.

Versión académica local, 2026-11-19. Inicio de servicios: [guía de instalación y ejecución](INICIAR_SERVICIOS.md). Cuenta disponible: [admin / admin](LOGIN_ADMIN.md).

1. Abre `http://127.0.0.1:3000`. Introduce usuario **admin** y contraseña **admin**, y pulsa **Ingresar**. Si no hay conexión, inicia Flask y usa Reintentar conexión.
2. Pulsa **Seleccionar archivos**. Admite hasta 10 .xls/.xlsx/.csv, 10 MiB por archivo y 25 MiB por lote. Mantén la detección automática o elige un perfil compatible. No cargues ZIP.
3. Pulsa **1. Cargar archivos**. Revisa cuáles fueron admitidos y los motivos de rechazo. **Nueva carga** prepara otra selección; no elimina datos ya guardados.
4. Para comparar, incluye al menos dos archivos y selecciona por archivo las columnas de **Número de factura**, **NIT/CI** y **Monto numeral**. Si no existe una columna, elige No disponible. Elige el archivo de referencia y si compararás NIT, monto o ambos.
5. Pulsa **Buscar facturas y comparar**. El número de factura busca el registro; NIT/monto determinan igualdad o diferencia. La limpieza previa se ejecuta automáticamente si todavía falta.
6. Revisa por archivo Coincide, Difiere, No encontrado, Incompleto o Varias filas. **Ver filas de origen** muestra hoja/fila. No se suman montos ni se eliminan repeticiones. Los filtros del resultado y la paginación permiten enfocar la revisión.
7. Un aviso de filas sin número utilizable indica cuántas sí se buscaron. Despliega ubicación/motivo para revisar las restantes; no significa que todas las facturas fallaron. Las fórmulas y valores ambiguos no se inventan.
8. En **Resultado de la limpieza**, consulta Registros leídos/Observaciones y el filtro todos/válidos/observados. También puedes ejecutar solo **Limpiar y revisar registros** si no quieres comparar archivos. Selecciona modalidad y departamento para revisar el consolidado; **Descargar Excel limpio** incluye todos los válidos seleccionados y **Descargar observaciones** conserva todas las incidencias del lote. Las descargas abarcan todas las páginas. [Detalles y hojas del Excel](EXPORTACIONES.md).
9. Pulsa **Cerrar sesión** al terminar. La pantalla oculta el área de trabajo y la API exige volver a ingresar.

Los originales no se modifican. Los lotes duran 24 h lógicamente; su retirada física es un comando técnico explícito. La sesión dura hasta 8 h; cerrarla revoca las sesiones previas de esta misma cuenta. Recargar conserva una sesión válida, pero todavía no recupera el lote en pantalla: será necesario realizar una carga nueva. No hay historial visual de lotes.

No hay edición/eliminación manual de facturas. La falta de NIT en el archivo de Vivian se informa; puede compararse solo monto si corresponde al objetivo de la revisión. Un observado puede participar en comparación, pero no entra como cabecera válida al Excel limpio por omitir su clasificación.

Detalles de formatos: [material](FORMATOS_MATERIAL.md), [febrero](FORMATOS_FEBRERO.md). Estados y reglas: [comparación](COMPARACION_FACTURAS.md). No se obtiene clasificación de modalidad/departamento por el nombre del archivo.
