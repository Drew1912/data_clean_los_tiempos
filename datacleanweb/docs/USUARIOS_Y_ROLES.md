# Usuarios, roles y permisos

Implementado por solicitud del responsable el 2026-11-24. Las exportaciones limpias y de observaciones siguen disponibles en Revisión para quienes tienen permiso de descarga.

Decisiones expresas: «editar» significa configurar columnas y ejecutar limpieza, sin edición manual de facturas; cada usuario consulta únicamente sus cargas. El administrador conserva acceso general para supervisión y es el único rol que gestiona cuentas. Estos perfiles iniciales no se presentan como una política empresarial validada.

| Rol | Cargar | Consultar propias | Configurar/limpiar | Comparar | Descargar | Gestionar usuarios | Auditoría |
|---|---|---|---|---|---|---|---|
| Administrador | Sí | Todas | Sí | Sí | Sí | Sí | Con permiso explícito |
| Cajas | Sí | Sí | Sí | Sí | No | No | No |
| Contabilidad | Sí | Sí | Sí | Sí | Sí | No | No |
| Solo lectura | No | Sí | No | Sí | No | No | No |
| Consulta y descarga | No | Sí | No | No | Sí | No | No |
| Solo carga de archivos | Sí | Solo estado/estructura de su carga | No | No | No | No | No |

La comparación calcula resultados sin modificar facturas; por eso Solo lectura puede comparar cargas ya procesadas. No ejecuta limpieza automática si falta ese permiso. Solo carga puede consultar perfiles de lectura y metadatos de sus archivos para saber si la importación fue admitida, pero no consultar filas ni descargar datos.

Un usuario que empieza sin permiso de cargar no tendrá cargas propias. Puede consultar las que creó cuando tenía otro rol. No se añadieron transferencias de propiedad ni un espacio de trabajo compartido: serían cambios de alcance que deben acordarse. El administrador puede abrir cualquier carga vigente para supervisión. Los lotes históricos sin autor no se asignan a nadie por suposición.

## Uso del administrador

1. Ingresa con admin y abre **Usuarios** en el menú izquierdo.
2. Introduce un nombre único de 3–50 caracteres: minúsculas, números, punto, guion o guion bajo; empieza por letra.
3. Asigna rol y contraseña inicial de 8–128 caracteres. El resumen muestra las capacidades antes de guardar.
4. Pulsa **Crear usuario**. No hay registro público de cuentas.
5. **Editar** permite cambiar rol, activar/desactivar, restablecer contraseña y, para administradores, permitir auditoría. El nombre permanece fijo. Una contraseña vacía en edición conserva la anterior.

No se borran usuarios: desactivar conserva su identidad, cargas y eventos. Toda modificación de cuenta revoca sus sesiones anteriores. No se permite desactivar ni degradar al admin original ni a la cuenta administradora que está realizando el cambio. Cambiar los propios datos revoca la sesión y exige ingresar de nuevo.

La contraseña original admin/admin se conserva al migrar, por compatibilidad con la demostración anterior. Las cuentas nuevas y restablecimientos exigen ocho caracteres como mínimo; `inicializar-admin` nunca reemplaza una contraseña existente. La pantalla de acceso ya no publica credenciales de demostración.

## Uso de otras cuentas

El menú y los botones se ajustan al rol. **Importación → Cargas disponibles** permite abrir una carga propia después de recargar la página o iniciar sesión nuevamente. La recuperación conserva sus resultados y clasificación guardados; las selecciones de comparación se configuran de nuevo. Los lotes vencidos se muestran sin botón habilitado; se mantiene la retención lógica de 24 horas y la purga técnica existente.

No basta ocultar botones: Flask comprueba sesión, capacidades y propietario en cada petición. Una acción no permitida devuelve 403. Una carga ajena devuelve 404 sin informar sus datos; estar autenticado y conocer un UUID no concede acceso. Las sesiones revocadas/inactivas reciben 401. La lista de cargas se filtra por autor en SQL.

## Base de datos y API

Migración idempotente `backend/db/006_usuarios_roles.sql`: retira las restricciones de usuario único, añade secuencia de IDs y `usuario.rol`, mantiene hashes y autorías, crea índice de nombre sin distinción de mayúsculas y amplía los eventos de auditoría. La cuenta existente id=1 se convierte en Administrador solo al añadir la columna; repetir la migración no altera otros roles, estados ni contraseñas.

Se mantienen **6 tablas y 69 atributos**, con un código de rol en usuario. La matriz de permisos se centraliza en `backend/app/services/permissions.py`; no se crea un catálogo de áreas empresariales ni una tabla de asignaciones arbitrarias. `usuario.puede_ver_auditoria` se conserva como permiso adicional del rol Administrador.

| Método y ruta | Acceso y resultado |
|---|---|
| GET `/api/v1/usuarios?pagina=1&tamano=25` | Administrador; cuentas paginadas y catálogo de perfiles/permisos |
| POST `/api/v1/usuarios` | Administrador y CSRF; nombre, contraseña, rol y opcionalmente activo/permiso de auditoría; 201 |
| PATCH `/api/v1/usuarios/{id}` | Administrador y CSRF; rol/estado/contraseña/permiso de auditoría; 200 |
| GET `/api/v1/lotes?pagina=1&tamano=10` | Lista propia; administrador ve todas, incluyendo lotes históricos sin autor |
| GET `/api/v1/auth/sesion` | Devuelve usuario con id, nombre, rol, permisos efectivos y permiso de auditoría; nunca hash |

Las rutas anteriores conservan sus contratos y añaden autorización por rol y propietario. Las contraseñas se guardan con scrypt y no se devuelven. Los nuevos eventos son USUARIO_CREADO, USUARIO_ACTUALIZADO y USUARIOS_ACCESO para rechazos de consulta; el detalle contiene ID afectado, rol, estado y si cambió la credencial, sin guardarla. El historial mantiene su retención independiente.

## Actualización y pruebas reproducibles

Con PostgreSQL iniciado y desde la raíz:

```powershell
$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
& .\.venv\Scripts\python.exe -m flask --app backend.app:create_app actualizar-esquema
& .\.venv\Scripts\python.exe -m flask --app backend.app:create_app inicializar-admin
```

Reinicia Flask. Detén Next.js con Ctrl+C en su terminal, entra en frontend, ejecuta `npm.cmd run build` y `npm.cmd run start`. [Comandos completos por servicio](INICIAR_SERVICIOS.md).

```powershell
$env:TEST_DATABASE_URL=$env:DATABASE_URL
& .\.venv\Scripts\python.exe -m pytest backend/tests/test_users_roles.py -q
```

La suite crea esquemas aleatorios de PostgreSQL y prueba roles, propiedad, escalamiento de privilegios, hash, filtrado de cargas, contraseñas, desactivación, revocación de sesiones, CSRF, migración repetida y conservación de registros. No crea cuentas de prueba en la base operativa.

Pendientes fuera de esta entrega: creación de roles personalizados, transferir cargas, permisos por área/departamento, recuperación de contraseña por correo, edición manual de facturas y validación empresarial de la matriz. No se presenta la instalación local como un despliegue de producción.

## Evidencia ejecutada — 2026-11-24

- Migración 006 aplicada en PostgreSQL local, conservando la cuenta admin y los datos existentes. Repetición de migraciones probada sin restablecer roles, contraseñas ni estados.
- **197 pruebas del backend aprobadas en 299,71 s**, incluidas 16 nuevas de usuarios/roles y las de comparación, revisión, exportación y auditoría. PostgreSQL con esquemas aislados.
- Compilación de producción Next.js y TypeScript aprobadas en un directorio separado para pruebas.
- Chromium: creación y edición de cuentas desde la interfaz; operación con Contabilidad, Solo carga y Solo lectura; rechazo de acceso a una carga ajena; recuperación de carga propia; ausencia de botones no autorizados y acceso directo a Usuarios bloqueado. Sin errores JavaScript ni desborde a 390 px.
- Regresión del administrador en Chromium: importación de dos Excel ficticios, columnas de contrato, comparación, limpieza, filtro Crédito, descarga, conservación al navegar, atrás/adelante, Nueva carga y cierre de sesión. Vistas de 768/390 px aprobadas.
- Capturas con datos ficticios: [Administrador](evidencias_cierre/usuarios_admin.png), [móvil](evidencias_cierre/usuarios_movil.png), [Solo carga](evidencias_cierre/usuario_solo_carga.png), [Solo lectura](evidencias_cierre/usuario_solo_lectura.png).
- Docker Compose y validación con personal de la empresa no ejecutados en esta entrega.
