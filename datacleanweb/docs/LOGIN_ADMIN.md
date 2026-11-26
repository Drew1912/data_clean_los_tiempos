# Acceso del administrador de demostración

> **2026-11-24, usuarios y roles:** [Entrega vigente](USUARIOS_Y_ROLES.md). Cuentas administradas exclusivamente por Administrador; permisos por rol y consultas limitadas a cargas propias, con acceso general del administrador. Incluye recuperar cargas vigentes. Modelo actual: 6 tablas/69 atributos; usuario tiene 8 campos. Las referencias anteriores a cuenta unica, falta de roles o 68 atributos son antecedentes. Migracion 006 ya aplicada en la base local; reiniciar Flask y recompilar/reiniciar Next.js.


> **Actualización 2026-11-24:** [Auditoría implementada](AUDITORIA.md): historial persistente de accesos y operaciones, permiso de consulta comprobado en Flask y nueva página en el menú. Migración 005; el modelo vigente tiene 6 tablas y 68 atributos. Las referencias anteriores a ausencia de historial o cinco tablas describen entregas previas.


Modelo de datos: [DER vigente con usuarios y relaciones del caso de estudio](DER_ACTUAL.md), con figuras PNG/SVG y diccionario. La tabla usuario ya está implementada; Cajas, Contabilidad y Sistemas mantienen sus responsabilidades conceptuales, sin roles adicionales de acceso.

Ampliación autorizada el 2026-11-19 para la actividad de cierre. Usuario **admin**, contraseña **admin**. Es una cuenta académica local, no una contraseña personal ni un despliegue empresarial.

## Activar en una instalación existente

Con PostgreSQL iniciado, desde PowerShell:

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb\backend'
$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
..\.venv\Scripts\python.exe -m flask --app app:create_app actualizar-esquema
..\.venv\Scripts\python.exe -m flask --app app:create_app inicializar-admin
..\.venv\Scripts\python.exe -m flask --app app:create_app run --host=127.0.0.1 --port=8000 --no-debugger --no-reload
```

En otra terminal:

```powershell
Set-Location 'C:\Users\ANDREW\Desktop\8VO_SEMESTRE\PRACTICA_EMPRESARIAL\proyecto_los_tiempos\datacleanweb\frontend'
$env:BACKEND_URL='http://127.0.0.1:8000'
$env:PORT='3000'
npm.cmd run build
npm.cmd run start
```

Abre `http://127.0.0.1:3000`, recarga e ingresa admin / admin. Detén previamente con Ctrl+C los servidores abiertos en esos puertos. En este equipo ya se aplicó la migración y se creó la cuenta; repetir los dos comandos CLI conserva datos y contraseña existente. Nunca se ejecuta un reinicio de contraseña al arrancar.

Compose incorpora estos comandos al inicio del backend y conserva la clave de sesión en el volumen privado. Su ejecución con Docker sigue pendiente de verificación en un equipo con Docker disponible.

## Qué protege

- Formulario con campos etiquetados, contraseña oculta inicialmente, opción de mostrarla y mensajes de credenciales incorrectas/conexión.
- Todas las rutas del blueprint de lotes, incluido perfiles, exigen sesión válida en Flask; acceder directamente a la API tampoco permite eludir el login.
- Cookie firmada `dataclean_session`, HttpOnly, SameSite=Lax, duración máxima 8 h, sin renovación automática por consultas. El usuario/versión se cotejan en PostgreSQL en cada petición protegida.
- Las operaciones POST, incluido login/logout, exigen `X-CSRF-Token`, obtenido por el cliente desde la sesión del mismo origen. El proxy Next.js transmite cookie/CSRF y devuelve Set-Cookie sin guardarlos en localStorage.
- Logout incrementa `version_sesion`: revoca también cookies copiadas y sesiones anteriores de la misma cuenta en otros navegadores. Solo hay una cuenta; no hay roles, registro público, recuperación ni administración de usuarios.
- La contraseña se guarda como hash scrypt mediante Werkzeug, nunca como texto plano. Tabla `usuario` con id=1 y nombre=admin restringidos por CHECK; FK nullable `lote.creado_por`. Los lotes previos conservan autor NULL; todos son accesibles al administrador único.
- La clave de firma se genera y conserva en `backend/temporales/.session-key`, o se recibe mediante `SECRET_KEY`. Cambiarla invalida sesiones. Nunca copiarla a documentación o repositorios; la carpeta está ignorada. `SESSION_COOKIE_SECURE=true` queda disponible para un futuro entorno HTTPS; el entorno local usa HTTP.

`GET /api/v1/health` y `GET /api/v1/auth/sesion` son públicos. La salud verifica las cinco tablas, sin devolver datos de facturas. Ejemplos ficticios estáticos siguen disponibles sin sesión. El HTML inicial es público y muestra el login; los datos están protegidos por la API.

## Contrato aditivo

| Método / ruta | Petición / respuesta |
|---|---|
| GET /api/v1/auth/sesion | Devuelve usuario `{nombre}` o null y csrf_token; no devuelve hash ni contraseña |
| POST /api/v1/auth/login | JSON `{usuario, contrasena}` + CSRF; devuelve usuario/csrf nuevos y cookie |
| POST /api/v1/auth/logout | CSRF y sesión; devuelve estado sesion_cerrada y revoca versión anterior |

Errores: 400 campos inválidos, 401 credenciales/sesión inválidas, 403 CSRF ausente/incorrecto, 415 tipo de petición, 503 base no disponible. Las rutas de facturación conservan sus formatos y añaden la exigencia transversal de autenticación/CSRF. El script HTTP de demostración se actualizó para iniciar/cerrar sesión.

Limitaciones: credenciales deliberadamente simples para demostración; no hay recuperación de contraseña, segundo factor, bloqueo por intentos o auditoría completa de accesos. No se afirma seguridad de producción. La cuenta puede leer todos los lotes temporales: no hay separación entre usuarios.
