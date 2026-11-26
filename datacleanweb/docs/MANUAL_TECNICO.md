# Manual técnico — versión académica

> **2026-11-24, usuarios y roles:** [Entrega vigente](USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **Actualización 2026-11-24:** [Auditoría implementada](AUDITORIA.md): historial persistente de accesos y operaciones, permiso de consulta comprobado en Flask y nueva página en el menú. Migración 005; el modelo vigente tiene 6 tablas y 68 atributos. Las referencias anteriores a ausencia de historial o cinco tablas describen entregas previas.


Actualización de interfaz 2026-11-23: rutas `/importacion`, `/comparacion`, `/revision` bajo `frontend/src/app/(workspace)`. El layout compartido monta `WorkspaceShell`, el acceso y `InvoiceWorkspace`; los paneles mantienen su estado al navegar y solo la página activa es visible/accesible. La comparación permanece montada para conservar selecciones y resultados. `/` redirige a Importación. No cambian API, SQL ni procesamiento.

Verificación de esta entrega: TypeScript y compilación de producción aprobados, con las tres rutas generadas; navegador en 1440/768/390 px, estados vacíos, conservación de archivos/contratos/lote/filtros/resultados, Atrás/Adelante, descarga Crédito reabierta, Nueva carga y logout aprobados, sin errores JavaScript. Capturas en `docs/evidencias_cierre/navegacion_*.png`. No se repitió la suite del backend por este cambio de interfaz; su última ejecución documentada conserva 157 aprobadas.

La comprobación utilizó compilación separada mediante `NEXT_DIST_DIR=.test-data/navigation-next`, con servicios de QA en 13000/18000 y un esquema aislado. `next.config.ts` y `start-local.cjs` admiten esa variable opcional; en uso normal se omite y se utiliza `.next`, con los mismos comandos anteriores. No se reemplazó la compilación que el usuario tenía en ejecución durante las pruebas. Los archivos de tipos autogenerados se restauraron a sus referencias habituales al finalizar.

Actualización de salida 2026-11-23: [filtros y exportaciones implementados](EXPORTACIONES.md). `backend/app/services/exportation.py` genera XLSX con openpyxl; repositorio serializa por lote y conserva ultima_exportacion; cliente/proxy transmiten binarios autenticados. No hay tablas ni dependencias nuevas.

2026-11-19. Arquitectura local: navegador → Next.js/React/TypeScript → proxy `/api/v1/*` → Flask → PostgreSQL 17. El frontend sirve HTML y recursos; las rutas de datos se validan en Flask. No hay servicios externos para procesar facturas.

| Carpeta | Responsabilidad |
|---|---|
| frontend/src/app | Página, estilos y proxy HTTP |
| frontend/src/components | Acceso, carga, comparación, resultados |
| frontend/src/lib/api.ts | Cliente HTTP, CSRF en memoria y manejo de sesión vencida |
| backend/app/routes | Salud, autenticación y lotes |
| backend/app/services | Carga, limpieza decimal, comparación, autenticación |
| backend/app/readers | Lectura CSV/XLSX/XLS, sin evaluar fórmulas |
| backend/app/profiles | Hojas, cabeceras y alias explícitos versionados |
| backend/app/repositories | Consultas PostgreSQL parametrizadas |
| backend/db | Migraciones idempotentes |
| backend/tests | Pruebas pytest con datos ficticios; integración por esquema aislado |
| tools | Generación de ejemplos y comprobaciones HTTP |

Dependencias exactas: `backend/requirements.txt`, `backend/requirements-dev.txt`, `frontend/package.json` y lockfile. Stack: Flask, psycopg, openpyxl y xlrd; Next.js/React/TypeScript. No se usa Pandas para inferir identificadores o dinero: Decimal y valores fuente preservan ceros y precisión. No se añadieron bibliotecas para el login: Flask/Werkzeug suministran sesiones y hash.

Modelo actual: **usuario → lote → archivo → registro**, con **observacion** asociada a archivo y opcionalmente registro. [DER y diccionario](fase_1/02_DATOS.md), [DER SVG](fase_1/diagramas/entidad_relacion.svg), [DDL](fase_1/schema_propuesto.sql). Cuenta única restringida por esquema; FK de autor nullable para lotes previos. Cargas guardadas con UUID/hash, originales y cambios en JSONB; importes NUMERIC sin escala fija. No hay tablas maestras inventadas ni roles empresariales.

Instalación/arranque: [servicios uno por uno](INICIAR_SERVICIOS.md). Actualización del login: [migración, cuenta y sesión](LOGIN_ADMIN.md). La base existente no se reinicializa. En Compose se aplican migraciones y se crea el administrador si todavía no existe. Docker está definido, pero su arranque no se verificó en esta revisión.

Contratos: [API base y ampliaciones](fase_1/03_API.md), [comparación](COMPARACION_FACTURAS.md), [autenticación](LOGIN_ADMIN.md). Los POST de datos ahora requieren cookie y CSRF. El healthcheck no exige autenticación y solo devuelve disponibilidad.

Retención: lotes con vencimiento lógico de 24 h; archivos privados en UPLOAD_ROOT. Limpieza física explícita `python -m flask --app app:create_app limpiar-cargas-vencidas`; no es un botón de borrar registros individuales. La clave de firma permanece en temporales/.session-key o SECRET_KEY y no se incluye en capturas/repositorio. Variables de conexión y claves personales no se documentan; `.env.example` contiene únicamente ejemplos.

Pruebas desde la raíz con la instancia aislada de PostgreSQL iniciada:

```powershell
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
```

Pruebas HTTP con servicios iniciados: `python tools/smoke_connectivity.py` y `python tools/smoke_upload_cleaning.py`. Este último utiliza solo el CSV ficticio e inicia/cierra sesión con la cuenta demo. Estado y evidencia actual: [revisión de la actividad final](REVISION_ACTIVIDAD_FINAL.md). No se declara aprobado el benchmark completo RNF-02 ni la aceptación empresarial.
