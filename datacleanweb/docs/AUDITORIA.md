# Historial de auditoría

> **2026-11-24, usuarios y roles:** [Entrega vigente](USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


Implementado el 2026-11-24 por solicitud del responsable del proyecto. En el menú izquierdo, **Auditoría** permite consultar fecha y hora, usuario, acción, resultado, lote y cantidades. Las fechas se presentan y filtran en horario de Bolivia (`America/La_Paz`); PostgreSQL guarda instantes con zona horaria.

## Acceso y eventos

La cuenta admin queda habilitada con `usuario.puede_ver_auditoria=true`. El menú se oculta sin ese permiso y Flask comprueba la sesión y el permiso en cada consulta: devuelve 401 sin sesión y 403 sin autorización. No depende de ocultar el enlace. Se conserva la cuenta única de demostración; no se añadió administración de usuarios ni roles múltiples.

Se registran creación inicial del administrador, inicio de sesión correcto o rechazado, cierre de sesión, carga de archivos, configuración de clasificación, procesamiento, comparación, generación de Excel limpio/reporte y purga técnica de lotes vencidos. Los errores y rechazos de esas operaciones también generan eventos cuando la base está disponible. Las consultas del historial rechazadas se registran; las lecturas correctas no generan eventos repetitivos.

La comparación registra la primera página sin filtro de resultados de cada ejecución; consultar páginas siguientes no crea otra ejecución. Reintentar un procesamiento ya completado no registra otro procesamiento. «Excel generado» confirma la generación en el servidor, no que el usuario haya guardado el archivo en su equipo.

Los eventos guardan el usuario autenticado, identificador de lote y metadatos limitados a códigos, cantidades, modalidad y referencia de configuración. Un intento de ingreso fallido figura como **No autenticado**: el nombre escrito no prueba identidad. Las tareas de consola figuran como **Sistema**.

No se guardan contraseñas, hashes, cookies, tokens, NIT, montos, nombres de archivos ni contenido de facturas en la auditoría. El procesamiento registra cantidad de normalizaciones; el detalle por campo, original y resultado sigue en **Revisión** mientras el lote esté disponible.

## Persistencia y límites

La migración `backend/db/005_auditoria.sql` añade el permiso y la tabla `auditoria`. Es repetible y no vuelve a conceder un permiso revocado. En una instalación nueva, `inicializar-admin` crea la cuenta con permiso; tampoco modifica una cuenta existente.

Los eventos de carga, clasificación, procesamiento, exportación y purga se insertan dentro de la transacción de la operación. Un fallo al guardar el evento revierte esa transacción. Los rechazos se guardan en una transacción separada; si PostgreSQL está caído, no se puede garantizar su persistencia y el servidor informa `AUDITORIA_NO_DISPONIBLE` sin imprimir datos privados.

`auditoria.usuario_id` es una FK nullable con `ON DELETE SET NULL`; `usuario_nombre` conserva la identidad histórica. `auditoria.lote_id` es una referencia UUID **sin FK**: los eventos permanecen después de la purga de lotes. No hay borrado automático del historial ni reconstrucción de actividad anterior a esta actualización. La política de retención y copias de seguridad para producción sigue pendiente.

La aplicación solo expone consulta del historial; no ofrece editar o eliminar eventos. Esto no impide que un administrador con acceso directo a PostgreSQL modifique la base: no se presenta como almacenamiento inviolable.

## Ejecución

Sigue [INICIAR_SERVICIOS.md](INICIAR_SERVICIOS.md). Con PostgreSQL iniciado, desde la raíz y usando el mismo `DATABASE_URL` del backend:

```powershell
& .\.venv\Scripts\python.exe -m flask --app backend.app:create_app actualizar-esquema
& .\.venv\Scripts\python.exe -m flask --app backend.app:create_app inicializar-admin
```

Reinicia Flask. En la terminal de Next.js, detén el servidor con Ctrl+C y ejecuta:

```powershell
Set-Location frontend
npm.cmd run build
npm.cmd run start
```

Ingresa con la cuenta admin, realiza una carga o procesamiento y abre **Auditoría**. Puedes filtrar por fechas, acción, resultado, usuario exacto y UUID de lote; «Actualizar historial» vuelve a consultar la base.

## API y verificación reproducible

`GET /api/v1/auditoria`: filtros opcionales `desde`, `hasta` (AAAA-MM-DD, ambos días incluidos), `accion`, `resultado` (`exito`, `rechazado`, `error`), `usuario`, `lote_id`, `pagina` y `tamano`. Respuesta paginada `datos`, `total`, `pagina`, `tamano`, `acciones`; eventos ordenados por fecha e ID descendentes. La interfaz usa 25 eventos por página. Filtros inválidos devuelven 400. POST/PATCH/DELETE no están implementados.

Con un PostgreSQL destinado a pruebas, desde la raíz:

```powershell
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
& .\.venv\Scripts\python.exe -m pytest backend/tests/test_auditing.py -q
```

Las pruebas crean y eliminan esquemas aislados: comprueban permisos, fechas de Bolivia, filtros, paginación, ingresos y salidas, ausencia de datos privados, reversión de escritura y conservación tras purga. La cuenta sin permiso se simula revocándolo dentro del esquema de prueba; no se afirma que exista un gestor de múltiples cuentas.

## Evidencia ejecutada — 2026-11-24

- PostgreSQL 17: migración 005 ejecutada, repetición sin pérdida de datos ni restitución de permisos revocados.
- Suite completa del backend: **173 pruebas aprobadas en 161,61 s**, con esquemas PostgreSQL aislados; incluye 16 casos de auditoría.
- Frontend compilado en directorio de prueba separado y servido con Next.js; Chromium comprobó acceso admin, cuatro enlaces del menú, consulta real, filtro por acción, cierre de sesión y rechazo 401 posterior. Capturas [escritorio](evidencias_cierre/auditoria_desktop.png) y [móvil](evidencias_cierre/auditoria_movil.png), sin desborde a 390 px.
- Regresión en Chromium: carga de dos Excel ficticios, selección de contrato, comparación, limpieza, filtro Crédito y descarga; los datos permanecen al navegar y usar atrás/adelante. También se comprobaron Nueva carga y vistas de 768/390 px. TypeScript sin errores. Servicios de QA detenidos y esquema temporal eliminado al terminar.
- No se ejecutó Docker Compose en esta entrega. Gestión de múltiples cuentas, política de retención de auditoría, recuperación de respaldos y despliegue de producción siguen pendientes; no se presentan como funciones probadas.
