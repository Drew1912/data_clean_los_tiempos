# Clasificar Contado y Crédito mediante el contrato

Cambio confirmado por el responsable el 2026-11-23: elegir la columna de contrato por archivo; **P al inicio = Crédito**, **C al inicio = Contado**. El departamento se retira del alcance operativo actual porque las fuentes no ofrecen una columna fiable para determinarlo.

## Uso actual

La columna de contrato se elige en la página **Importación**. Después puedes abrir **Comparación** o **Revisión** desde el menú lateral sin perder esa selección. [Guía de navegación](MANUAL_USUARIO.md#navegación-por-páginas).

1. Inicia sesión y realiza una **Nueva carga**. Se conservan los lotes y originales anteriores; no se reclasifican en segundo plano.
2. Después de cargar, cada archivo admitido muestra **Columna de contrato para Contado/Crédito**. Elige su cabecera real: por ejemplo `CONTRATO ` o `Numero Contrato`, según el libro. Las opciones provienen del archivo; no se selecciona una columna solo por el nombre del archivo.
3. Si la fuente no tiene contrato, deja **Sin contrato: usar columna C/P si existe**. Si tampoco tiene C/P, la modalidad queda sin clasificar y se informa como observado; sus datos todavía pueden compararse.
4. Pulsa **Limpiar y revisar registros** o **Buscar facturas y comparar**. Ambas acciones envían la selección antes de procesar. Después de procesar, la selección queda fija para mantener trazabilidad; un cambio requiere otra carga.
5. Usa el filtro **Modalidad: Todos / Contado / Crédito** y descarga el Excel limpio u observaciones. No hay selector de departamento ni columna departamental en el consolidado.

Se recortan espacios exteriores y se reconoce el prefijo sin distinguir mayúscula/minúscula. El contrato completo se conserva intacto en originales/adicionales. Ejemplos ficticios: `C-0001` → Contado; ` P-0002 ` → Crédito; `000123`, `X-001`, vacío o fórmula → observado, sin modalidad inventada. No se evalúan fórmulas ni se convierten fechas en contratos.

El contrato seleccionado tiene prioridad sobre la antigua columna C/P. Si esta contiene C o P y contradice el prefijo del contrato, se añade un aviso visible; ambos originales se conservan. La regla y la columna elegida quedan registradas en cambios y perfil_snapshot. La hoja Archivos del Excel identifica columna_contrato.

## Validación y datos anteriores

- En el flujo nuevo, CAJA/departamento no son obligatorios ni causan errores de clasificación. CAJA puede conservarse como dato de origen; departamento no se infiere. Las columnas SQL permanecen para compatibilidad y lotes históricos.
- Factura, fecha, NIT/CI, monto y modalidad siguen siendo obligatorios para una cabecera válida. Retirar departamento no rellena NIT ausente ni valida importes ambiguos. Los detalles de productos siguen observados y no se suman como facturas.
- La migración 004 sustituye únicamente la restricción de campos obligatorios de registro. Mantiene PK/FK, datos existentes, estados y coherencia C/P–modalidad. No elimina observaciones ni restablece exportaciones de lotes anteriores.
- La interfaz envía la configuración nueva incluso cuando no se elige contrato, desactivando departamento y usando C/P si existe. Una petición antigua de procesamiento sin cuerpo conserva el comportamiento de su perfil para compatibilidad de integraciones. Los filtros de departamento antiguos de la API se mantienen para consultar datos históricos, pero no se usan en la interfaz.

## Actualización en otra copia

En este equipo la migración ya se aplicó. En una copia anterior, con PostgreSQL iniciado, ejecuta desde backend:

```powershell
$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
..\.venv\Scripts\python.exe -m flask --app app:create_app actualizar-esquema
```

Reinicia Flask y recompila/reinicia Next.js según [INICIAR_SERVICIOS.md](INICIAR_SERVICIOS.md). Recarga el navegador y crea una carga nueva. Las migraciones son idempotentes y Compose también las ejecuta al iniciar el backend. Los ejemplos anteriores basados en CAJA/departamento son antecedentes del alcance previo.

## API aditiva

`POST /api/v1/lotes/{id}/procesamiento` admite ahora JSON con selección para **todos los archivos admitidos**, sesión y CSRF:

```json
{
  "contratos": [
    {"archivo_id": "UUID_DEVUELTO_POR_LA_CARGA", "columna": "CONTRATO "},
    {"archivo_id": "OTRO_UUID", "columna": null}
  ]
}
```

Se rechazan IDs ajenos/repetidos, columnas desconocidas, omisión de admitidos o estructura inválida con 400, sin iniciar el procesamiento. Repetir la misma configuración de un lote completado es idempotente; intentar otra devuelve 409 con indicación de crear una carga nueva. La descripción de archivo añade columna_contrato. La comparación sigue buscando por factura y comparando NIT/monto.

## Trazabilidad de requisitos

Este cambio sustituye la fuente C/P prevista para RF-03 cuando se elige contrato, y retira **RF-04 y RF-06** del alcance operativo por instrucción expresa del responsable. La base aprobada en REQUSITOS.md permanece intacta como antecedente: no se afirma que retirar departamento equivalga a cumplir su requisito original. La documentación de entrega debe explicar la modificación de alcance al docente/empresa.

RF-01/02/07/08/09/10/11/12 conservan su finalidad con modalidad por contrato, sin inventar datos faltantes. No se añaden roles, tablas empresariales ni un catálogo departamental supuesto.

Pruebas específicas: `backend/tests/test_contract_classification.py`: prefijos, ausencia de CAJA/departamento, fórmulas/vacíos, falta de NIT, prioridad/conflictos, filtros/exportación, validación de selección, idempotencia y migración desde restricción anterior. Los fixtures son ficticios; las observaciones de los datos originales no se borran.

Resultado ejecutado: **157 pruebas aprobadas en 121,19 s**, TypeScript y compilación de producción aprobados. La prueba en navegador usó dos libros ficticios sin CAJA ni departamento, con contratos C/P/X: selección por archivo, cuatro válidos C/P, dos observados X, filtro Crédito, comparación conservada, descarga de dos registros, vista móvil 390 px y cierre de sesión, sin errores JavaScript. El Excel guardado se reabrió: modalidad Crédito y código P, NIT textual, columna de contrato documentada y ninguna columna departamento. [Captura](evidencias_cierre/contratos_modalidad.png).

Se contrastaron las cabeceras y prefijos de contrato de las fuentes indicadas de La Paz, Daniel, Mónica y Vivian en modo lectura, contando C/P/otros sin imprimir valores de clientes. Hay contratos sin prefijo C/P: no se clasifican a partir del nombre de la hoja o del archivo. La migración se aplicó a la instancia local conservando datos. Docker no se ejecutó; la prueba de interfaz usó servicios y esquema de QA separados de los lotes del usuario.

Al terminar se detuvieron los servidores de QA y se retiraron su esquema y las copias privadas ficticias. PostgreSQL queda iniciado; el frontend actual ya está compilado. Para usar la regla, inicia Flask/Next.js y crea una carga nueva con la columna de contrato elegida.
