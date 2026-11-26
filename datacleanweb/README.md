# DataCleanWeb — Los Tiempos

## Instalar dependencias después de clonar

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location frontend
npm.cmd ci
```

El `requirements.txt` de la raíz incluye aplicación Python, pruebas y herramientas, con las versiones fijadas en `backend/requirements.txt` y `backend/requirements-dev.txt`; estos archivos también deben subirse a Git. La instalación local se ha probado con Python 3.11.9. El frontend conserva sus versiones en `frontend/package.json` y `frontend/package-lock.json`: subir ambos y utilizar `npm ci` para instalar las versiones del lockfile. Las imágenes Docker declaran Python 3.12 y Node.js 22, pero su ejecución sigue sin verificarse.

PostgreSQL 17 se instala por separado. Este paso solo instala dependencias: después hay que configurar y preparar la base e iniciar los servicios según el [manual técnico](docs/MANUAL_TECNICO.md) y la [guía de inicio](docs/INICIAR_SERVICIOS.md). Las rutas y la instancia local de esa guía corresponden al equipo original; cada compañero debe ajustarlas a su instalación.

> **2026-11-24, usuarios y roles:** [Entrega vigente](docs/USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **2026-11-24:** [Historial de auditoría](docs/AUDITORIA.md) implementado con acceso por permiso; seis tablas/68 atributos. GET `/api/v1/auditoria` devuelve eventos paginados; la respuesta de sesión incluye `usuario.puede_ver_auditoria`. Se conservan contratos operativos anteriores.


**Interfaz por etapas:** páginas Importación, Comparación y Revisión, con menú lateral y conservación del trabajo al navegar. [Uso y capturas](docs/MANUAL_USUARIO.md#navegación-por-páginas). Para actualizar el frontend, detenerlo, ejecutar `npm.cmd run build` y `npm.cmd run start`.

**Clasificación actual:** [seleccionar contrato por archivo: C = Contado, P = Crédito; sin departamento](docs/MODALIDAD_CONTRATO.md). Migración 004, ya aplicada en este equipo; reiniciar servicios y crear una carga nueva.

**Filtros y descargas:** [modalidad/departamento, Excel limpio y observaciones implementados](docs/EXPORTACIONES.md). Reinicia Flask y recompila/reinicia Next.js; no hay migración nueva.

**DER actualizado:** [usuarios, lotes, archivos, registros y observaciones; relación con el caso de estudio](docs/DER_ACTUAL.md). Incluye diagrama PNG/SVG y diccionario completo.

**Actividad final:** [estado de las cinco actividades y evaluación de experiencia de usuario (actividad 3)](docs/REVISION_ACTIVIDAD_FINAL.md). **Acceso:** admin / admin; [actualización y comandos](docs/LOGIN_ADMIN.md). [Manual de usuario](docs/MANUAL_USUARIO.md) · [Manual técnico](docs/MANUAL_TECNICO.md).

**Excel de febrero:** [perfiles para los nueve libros de «7MO_SEMESTRE/contado o credito»](docs/FORMATOS_FEBRERO.md). Reinicia Flask y crea una carga nueva con detección automática.

**Comparación configurable:** [cargar archivos, elegir columnas y buscar por factura para comparar NIT/CI y monto](docs/COMPARACION_FACTURAS.md). Incluye diferencias, ausencias y varias filas con origen; admite los perfiles de material además de los de demostración.

**Inicio paso a paso:** [comandos para iniciar PostgreSQL, Flask y Next.js por separado](docs/INICIAR_SERVICIOS.md).

**Formatos reales y matching:** [revisión de los cinco Excel de material, soporte .xls y correspondencias entre archivos](docs/FORMATOS_MATERIAL.md).

Estado: entrega de carga, limpieza y comparación configurable (Fase 2.2/2.3), sobre la infraestructura de Fase 2.1. Permite cargar Excel/CSV, normalizar formatos seguros, persistir filas/observaciones y comparar por factura en Next.js. Están habilitados perfiles de demostración y cuatro estructuras observadas en material; el catálogo empresarial completo sigue pendiente. `scripts/` se conserva como antecedente: se adaptaron sus etapas de lectura/normalización, sin importar su motor de conciliación ni sus descartes/redondeos.

- [Ejecución, pruebas y resultados reales de Fase 2.1](docs/fase_2_1/README.md).
- [Entregable de carga y limpieza: uso, reutilización de scripts y pruebas](docs/fase_2_2_3/README.md).
- [Correcciones C-01 a C-05, perfiles y diccionario](docs/fase_1/05_CORRECCIONES_CRITICAS.md).
- [Diseño de Fase 1](docs/fase_1/README.md).
- [Decisiones y evidencia pendiente](docs/DECISIONES_PENDIENTES.md).
- [To-Be v2 BPMN 2.0](docs/fase_1/diagramas/to_be_v2.bpmn).

Inicio local con Docker Desktop y Compose v2 disponibles:

```powershell
Copy-Item .env.example .env
# Editar .env y sustituir la clave de ejemplo antes de iniciar.
docker compose up --build --wait
python tools/smoke_connectivity.py
```

Si ya existe `.env`, conservarlo. Abrir `http://127.0.0.1:3000`, descargar uno de los ejemplos ficticios de la pantalla, elegir su perfil, cargar y pulsar «Limpiar y validar». Para ejecución sin Docker, seguir [las instrucciones locales](docs/fase_2_2_3/README.md). Docker no estaba disponible durante la revisión de infraestructura; no se afirma que sus imágenes se hayan ejecutado. La descarga de reportes y las reglas empresariales avanzadas siguen pendientes.
