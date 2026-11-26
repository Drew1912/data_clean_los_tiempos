# Formatos reales de material y correspondencias

> **Cambio 2026-11-19:** el flujo principal de correspondencias descrito abajo queda sustituido por [comparación configurable por factura](COMPARACION_FACTURAS.md): selectores por archivo, referencia explícita, NIT/CI y monto como valores a comparar. La fecha no es llave. El mapeo y las estructuras de lectura de este documento se mantienen. Las reglas previas de candidatos son antecedentes y su API se conserva por compatibilidad.

Revisión: 2026-11-18. Fuente: carpeta `documentaciones/material` indicada por el usuario. Se leyeron los cinco originales en modo lectura, incluyendo hojas, cabeceras, tipos y filas. Se verificaron hashes antes/después: originales intactos. No se copiaron registros empresariales a fixtures, capturas ni archivos públicos; las pruebas de interfaz usan datos ficticios con la misma estructura.

## Por qué no se veían los registros

La primera entrega solo tenía perfiles DEMO, hoja Facturas y cabeceras uniformes. Los originales usan .xls binario, hojas Hoja1/ENERO/hoja1, fila 1 o 4, nombres diferentes y columnas faltantes. Además, la tabla anterior mostraba solo válidos: los registros sin C/P o CAJA quedaban únicamente en observaciones.

Ahora se admite .xls/.xlsx/.csv y se propone un perfil por firma de hojas/cabeceras, sin usar el nombre del archivo para clasificar. La pantalla muestra **todos los registros leídos por defecto**, incluidos observados y líneas de detalle; el filtro permite ver solo válidos. La consulta API conserva estado=valido como defecto para compatibilidad y añade estado=todos/observado.

## Estructuras revisadas

| Archivo | Hoja / cabecera | Tipo y mapeo |
|---|---|---|
| ventas_072025 ARMAR(1).xls | Hoja1 / fila 1 | Cabecera SAC: NRO FACTURA→numero_factura, FCH. FACTURA→fecha_factura, NIT/CI→nit_ci, RAZON SOCIAL FACTURA→razon_social, C ò P→modalidad_codigo, CAJA→caja_codigo, Importe total de la factura→monto_numeral |
| ventas1_072025 ARMAR.xls | Hoja1 / fila 1 | Detalle: Nro FACTURA y CAJA para referencia; COD. PRODUCTO, CANTIDAD, PRECIO UNITARIO, SUBTOTAL e IMPORTE TOTAL permanecen como datos de línea, no total de cabecera |
| CONTADO - 2026-2.xlsx | ENERO / fila 4 | FACTURA→numero_factura, FECHA→fecha_factura, NIT→nit_ci, MONTO→monto_numeral, CLIENTE→razon_social; CONTRATO y resto conservados |
| CONTRATOS FACTURADOS 2026-2.xlsx | ENERO / fila 4 | Misma estructura base de control, con menos complementarias; no se exige que tenga columnas que no existen |
| FACTURAS SIAT ENE26 (1).xlsx | hoja1 / fila 1 | Nº DE LA FACTURA→numero_factura, FECHA DE LA FACTURA→fecha_factura, NIT / CI CLIENTE→nit_ci, IMPORTE TOTAL DE LA VENTA→monto_numeral, NOMBRE O RAZON SOCIAL→razon_social |

Los alias se configuran en backend/app/profiles/material.json. La vista «Correspondencia de columnas» de cada archivo muestra el mapeo que se aplicó. Si más de un perfil coincide o ninguno lo hace, se informa y se puede elegir un perfil explícito. No hay coincidencia difusa de cualquier columna que contenga «total».

### Decisiones confirmadas y límites

- El usuario confirmó que en la cabecera SAC se debe usar **Importe total de la factura**. La columna G tiene como cabecera el número 1; se conserva sin asignarle significado. Si falta el total seleccionado, no se rellena con G ni con MONTO LITERIAL.
- Cufd -siat se conserva como adicional: CUFD no se equipara a CUF. Tampoco se toma CODIGO DE AUTORIZACIÓN del SIAT como CUF por suposición.
- Se observaron cajas completas 0C/1C en las muestras. Ese catálogo se usa en sus perfiles; no se inventan otras cajas válidas. No se infiere Contado/Crédito del nombre del archivo ni se deducen departamentos de cualquier letra suelta.
- Los controles y SIAT no tienen C/P/CAJA. Se limpian sus campos presentes y se observan los faltantes; los datos siguen visibles y pueden participar en correspondencias con claves suficientes.
- Las columnas sin cabecera y sin datos se ignoran estructuralmente. Cuando sí contienen datos, se conservan bajo un nombre técnico como columna_sin_cabecera_M y se informa; no se les asigna un campo de negocio.
- Los detalles no se eliminan ni se confunden con facturas duplicadas. Se guardan con su nivel derivado del perfil, fuera del conjunto de cabeceras válidas. Los contadores de observados incluyen las referencias de detalle no consolidables, además de errores/faltantes.
- xlrd 2.0.2 lee .xls BIFF8; openpyxl continúa leyendo .xlsx. Los números BIFF son IEEE754: se conserva su representación y hexadecimal originales, se tratan identificadores enteros con precaución y no se reconstruye precisión perdida. Se detectan registros FORMULA BIFF sin evaluar su expresión ni confiar en su resultado almacenado.

## Correspondencias entre archivos

El usuario aclaró que solicita tanto mapeo de columnas como relación de facturas. Se incorpora una vista de vínculos propuestos, sin concatenaciones destructivas ni reconstrucción de campos ausentes.

| Tipo | Regla | Tratamiento |
|---|---|---|
| Entre cabeceras | Número de factura + fecha + NIT/CI, entre archivos distintos y con cajas conocidas compatibles | Grupo candidato; si varían importes u otros valores se muestran los campos diferentes, sin escoger ganador |
| Cabecera y detalle | Número de factura + CAJA | Conservar una o varias líneas; sin sumar ni repetir el total de cabecera. Si hay varias cabeceras posibles, marcar ambiguo |
| Campos insuficientes | Sin identificador/fecha/NIT suficientes, o detalle sin caja | No inventar una correspondencia |

Para la comparación, números de factura exclusivamente numéricos pueden coincidir ignorando ceros iniciales; se avisa y se conservan todas las representaciones originales. Esto es una señal de correspondencia, no una declaración de identidad global. NIT/CI se compara como texto conservado. No se usa NIT+fecha+monto como llave ni CUFD como identificador de factura. No se rellenan automáticamente las columnas faltantes.

El nuevo GET `/api/v1/lotes/{id}/relaciones` devuelve grupos paginados, regla, candidatos, diferencias y origen. Se calcula sobre filas persistidas, sin nuevas tablas y sin cambiar los registros. Los detalles se mantienen separados mediante perfil_snapshot.nivel.

## Resultado real de lectura en memoria

Las cantidades incluyen filas vacías interiores, resúmenes o fórmulas que requieren revisión; no equivalen a una certificación de facturas.

| Fuente | Filas leídas | Válidas como cabecera | Observadas / referencia |
|---|---:|---:|---:|
| CONTADO - 2026-2.xlsx | 46 | 0 | 46 |
| CONTRATOS FACTURADOS 2026-2.xlsx | 25 | 0 | 25 |
| FACTURAS SIAT ENE26 (1).xlsx | 394 | 0 | 394 |
| ventas1_072025 ARMAR.xls | 25 | 0 | 25 |
| ventas_072025 ARMAR(1).xls | 18 | 8 | 10 |

Sobre los cinco archivos juntos: **65 grupos entre cabeceras y 12 cabecera-detalle**, como candidatos; 345 filas no tienen relación con las claves disponibles. Cero válidos en una fuente sin clasificación no significa cero datos: ahora esas filas aparecen en «Registros leídos». No se persistieron datos empresariales como parte de esta comprobación en memoria.

## Cambio autorizado de formato y migración

RF-01 original menciona .xlsx/.csv. La solicitud reciente añade expresamente **.xls**: se registra esta ampliación, sin reescribir silenciosamente el requisito original. La relación entre archivos también fue aclarada expresamente por el usuario; no se reactiva la conciliación financiera histórica.

El modelo sigue teniendo cuatro tablas. Fue necesario ampliar el CHECK de archivo.extension para admitir .xls. `backend/db/002_admitir_xls.sql` es transaccional y repetible, no elimina datos. El DDL inicial ya contempla la extensión nueva para bases nuevas.

En este equipo la migración ya se aplicó. Para otra copia con base anterior, con PostgreSQL iniciado, desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
$env:DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
Set-Location backend
..\.venv\Scripts\python.exe -m flask --app app:create_app actualizar-esquema
```

Después iniciar Flask y Next.js con la [guía de servicios](INICIAR_SERVICIOS.md). Si actualizas fuentes frontend, ejecutar `npm.cmd run build` dentro de frontend antes de `npm.cmd run start`.

## Cómo probar tus documentos

1. Reinicia Flask y Next.js para cargar estos cambios; abre http://127.0.0.1:3000.
2. Selecciona los cinco archivos de material en un mismo lote.
3. Deja «Detectar por hojas y cabeceras», o selecciona el perfil explícito correspondiente.
4. Pulsa «Cargar archivos»; revisa el formato detectado y su correspondencia de columnas.
5. Pulsa «Limpiar y validar»; en «Registros leídos» deja «Todos los registros».
6. Abre «Correspondencias» para revisar cabeceras y líneas relacionadas; «Observaciones» explica los datos faltantes o dudosos.

No cambiar nombres de hojas ni convertir manualmente los .xls para estas estructuras. Los originales permanecen intactos.

## Evidencia y pruebas

- **94 pruebas pytest aprobadas**, sin omisiones, en 26,16 s en la ejecución registrada: incluye lectura BIFF, fórmulas, nombres de cabecera incompletos, total elegido, SIAT, campos ausentes, migración repetible, API y reglas de matching.
- Build Next.js y TypeScript correctos.
- Navegador: cuatro archivos ficticios con estructuras reales reconocidos automáticamente; cinco filas visibles (una válida y cuatro observadas), filtro todos/válidos y dos grupos de correspondencias; sin errores JavaScript ni desborde de página en móvil.
- [Captura de correspondencias con datos ficticios](fase_2_2_3/vista_correspondencias.png). Nunca se usaron datos reales en capturas públicas.
- No se acreditan conciliación contable, identidad global de factura, autorización empresarial de todos los catálogos ni ejecución Docker.

Trazabilidad: RF-01/02 (formatos y mapeo), RF-07/08 (limpieza y revisión), RF-09 (preservación estructural, sin agregación), RF-12 (cantidades); RNF-01/04/05/06 (originales, errores, módulos y datos privados). Exportaciones siguen pendientes.

Referencia de la biblioteca añadida por necesidad del formato: [xlrd y su soporte de .xls](https://xlrd.readthedocs.io/en/stable/).
