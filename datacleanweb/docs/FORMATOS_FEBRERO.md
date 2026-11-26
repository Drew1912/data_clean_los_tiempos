# Excel de «7MO_SEMESTRE/contado o credito»

Revisión: 2026-11-19. La detección anterior solo conocía las estructuras de `documentaciones/material`. Elegir manualmente uno de esos perfiles no resolvía las diferencias de hojas/cabeceras de estos libros. Se incorporan cuatro perfiles específicos, sin cambiar tablas ni contratos de carga/comparación.

## Cómo probarlos

1. En la terminal de Flask, pulsa Ctrl+C y vuelve a ejecutar el bloque de backend de [INICIAR_SERVICIOS.md](INICIAR_SERVICIOS.md). Los perfiles se cargan al iniciar el proceso.
2. Recarga la página del navegador y pulsa **Nueva carga**. Los lotes rechazados anteriores conservan su diagnóstico; no se reprocesan automáticamente con otro perfil.
3. Selecciona los Excel y deja **Detectar por hojas y cabeceras**. Los nueve libros revisados tienen exactamente un perfil compatible cada uno.
4. Elige columnas y archivo de referencia, y pulsa **Buscar facturas y comparar** como indica [la guía de comparación](COMPARACION_FACTURAS.md).

Este ajuste cambia solo el backend: no requiere migración SQL, reinstalar dependencias ni volver a compilar Next.js.

## Estructuras verificadas

| Archivo | Hoja y fila de cabecera | Perfil / filas leídas |
|---|---|---|
| CONTADO SCZ Febrero 2026.xlsx | FEBRERO, fila 1 | febrero_control_xlsx / 42 |
| Contratos Facturados LA PAZ 2026 corregido.xlsx | « FEBRERO CONTADO» y «FEBRERO CREDITO», fila 1 | febrero_control_xlsx / 184 |
| CREDITO SCZ Febrero 2026.xlsx | FEBRERO-TRYSTAR, fila 1 | febrero_control_xlsx / 7 |
| ventas Daniel Feb-26.xlsx | credito, fila 3; contado, fila 1 | febrero_control_xlsx / 40 |
| ventas monica feb-26.xlsx | CREDITO, fila 4; CONTADO, fila 1 | febrero_control_xlsx / 144 |
| ventas vivian feb-26.xlsx | febrero corregido, fila 1 | febrero_resumen_sin_nit_xlsx / 18 |
| FEBRERO/FEBRERO.xlsx | Hoja1, fila 1 | febrero_sac_cabecera_xlsx / 337 |
| FEBRERO/FEBRERO1.xlsx | Hoja1, fila 1 | febrero_sac_detalle_xlsx / 336 |
| FEBRERO/ventas siat feb-2026.xlsx | hoja1, fila 1 | material_siat_xlsx existente / 336 |

Los conteos incluyen vacíos interiores y filas sin clave que deben observarse; no equivalen a facturas únicas. Las hojas admitidas se leen juntas conservando hoja y fila de origen. Si una factura aparece en varias hojas del mismo archivo, la comparación la informa como varias filas y no elige una automáticamente.

Se conserva el espacio inicial real del nombre « FEBRERO CONTADO». No se infiere modalidad, departamento ni período a partir de nombres de archivos/hojas.

## Decisiones de lectura

- **Controles:** FACTURA → factura; NIT → NIT/CI; MONTO → monto; FECHA → fecha; CLIENTE → razón social. La fila de cabecera se configura por hoja, sin adivinación libre.
- **Vivian:** Numero Factura → factura; Fecha → fecha; Total Factura → monto; Nombre → razón social. No contiene columna NIT. Se carga con ese dato ausente: seleccionar comparación de NIT da incompleto; seleccionar solo monto permite comparar ese campo. No se completa el NIT desde otros archivos.
- **SAC febrero:** usa su columna explícita MONTO NUMERAL. Esta fuente es distinta del SAC .xls anterior, que conserva exclusivamente «Importe total de la factura» sin respaldo alternativo. Las etiquetas complementarias repetidas ESPACIO y 0 se distinguen por letra física, por ejemplo «ESPACIO [columna E]», conservando todos los valores. Las cabeceras de identidad repetidas siguen siendo error.
- **Detalle:** FEBRERO1.xlsx conserva líneas y sus importes como adicionales. No suma SUBTOTAL/IMPORTE TOTAL ni los convierte en total de cabecera; está excluido inicialmente de la selección para comparar.
- **Filas formateadas:** el libro de Mónica declara 1.048.576 filas. Se mide el contenido real del XML y se ignoran celdas sin valor ni fórmula que solo tienen estilo. Se conservan vacíos interiores; se siguen rechazando contenidos reales fuera de 5.000 filas de datos por lote/100 columnas, así como fórmulas fuera del límite. Se informa aviso de dimensión declarada excesiva.
- **Columnas sin cabecera:** las que contienen datos conservan nombres técnicos; no se les asigna significado por su posición. Fórmulas no se evalúan.
- **ZIP:** no se carga FEBRERO.zip directamente. La carpeta FEBRERO ya contiene los tres Excel extraídos; selecciónalos como archivos individuales.

## Evidencia

Los nueve originales se leyeron en modo lectura y se verificaron hashes antes/después, sin cambios. No se copiaron datos de clientes a los tests ni a capturas públicas. Las pruebas automatizadas usan libros ficticios con las mismas estructuras.

Suite ejecutada: **124 pruebas aprobadas**, incluidas cabeceras por hoja, espacio inicial en nombre, formato hasta última fila de Excel, conservación de columnas repetidas, rechazo de identidad duplicada y contenido real fuera de límites, resumen sin NIT, detalle y carga/limpieza/comparación mediante API con esquema PostgreSQL aislado. No se cambiaron componentes de interfaz; la prueba de navegador documentada anteriormente corresponde al flujo de comparación anterior y no se volvió a ejecutar para esta corrección del lector. Docker no se ejecutó.

Además de los fixtures ficticios, se ejecutó la carga conjunta de los **nueve originales** mediante el cliente de pruebas Flask: nueve admitidos, **1.444 filas conservadas**, procesamiento y comparación HTTP 200. Se usaron un esquema PostgreSQL aislado y copias privadas temporales; ambos se retiraron al finalizar. Los hashes de los originales permanecieron iguales. Esta prueba no modificó los lotes de la aplicación abierta por el usuario.

Para repetir los tests desde la raíz, con PostgreSQL de pruebas iniciado:

```powershell
$env:TEST_DATABASE_URL='host=127.0.0.1 port=55439 dbname=dataclean_test user=dataclean_test'
.\.venv\Scripts\python.exe -m pytest -q
```

Archivos de implementación: `backend/app/profiles/material.json`, `backend/app/readers/invoices.py`, `backend/app/services/importation.py`. Pruebas: `backend/tests/test_febrero_formats.py`.
