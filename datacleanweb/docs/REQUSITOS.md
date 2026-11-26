REQUISITOS DEL SISTEMA
Data Cleaning y consolidación de facturación – Editorial Canelas S.A. (Los Tiempos)
1. REQUISITOS FUNCIONALES (RF)
Código	Descripción del requisito	Prioridad
RF-01	El sistema deberá permitir importar uno o varios archivos de facturación en formatos Excel (.xlsx) y CSV (.csv).	Alta
RF-02	El sistema deberá reconocer y validar los nombres de columnas correspondientes a los formatos de facturación admitidos.	Alta
RF-03	El sistema deberá identificar automáticamente la modalidad de facturación mediante los valores C (Contado) y P (Crédito) de la columna «C o P».	Alta
RF-04	El sistema deberá identificar automáticamente el departamento mediante los códigos C (Cochabamba), L (La Paz) o S (Santa Cruz) contenidos en la columna «CAJA».	Alta
RF-05	El sistema deberá permitir filtrar los registros según la modalidad de facturación: Contado, Crédito o Todos.	Alta
RF-06	El sistema deberá permitir filtrar los registros según el departamento: Cochabamba, La Paz, Santa Cruz o Todos.	Alta
RF-07	El sistema deberá aplicar técnicas de Data Cleaning para normalizar NIT/CI, números de factura, fechas, importes y campos de texto.	Alta
RF-08	El sistema deberá identificar filas vacías, registros incompletos, valores incorrectos y posibles facturas duplicadas.	Alta
RF-09	El sistema deberá consolidar los registros válidos de los archivos cargados utilizando una estructura uniforme y conservando su modalidad y departamento de origen.	Alta
RF-10	El sistema deberá generar un archivo Excel con los registros limpios y filtrados según los criterios seleccionados.	Alta
RF-11	El sistema deberá generar un reporte separado con los registros que presenten errores, duplicidades o inconsistencias.	Alta
RF-12	El sistema deberá mostrar un resumen con la cantidad de registros cargados, válidos, observados y exportados.	Media

2. REQUISITOS NO FUNCIONALES (RNF)
Código	Categoría	Descripción del requisito	Criterio de aceptación
RNF-01	Integridad de datos	Los archivos originales no deberán modificarse ni sobrescribirse durante la limpieza y consolidación.	Los archivos de entrada permanecen intactos después del procesamiento.
RNF-02	Rendimiento	El sistema deberá procesar un volumen representativo de registros en un tiempo razonable.	Meta inicial: 1.000 registros por fuente en menos de 30 segundos, en un equipo de prueba definido.
RNF-03	Usabilidad	La interfaz deberá permitir ejecutar el flujo principal sin conocimientos de programación.	El usuario puede cargar archivos, seleccionar filtros, procesar y descargar el Excel desde una pantalla sencilla.
RNF-04	Confiabilidad	El sistema deberá detectar errores de formato y manejar archivos inválidos sin finalizar inesperadamente.	Ante un archivo incorrecto, muestra un mensaje comprensible y permite volver a cargar datos.
RNF-05	Mantenibilidad	La aplicación deberá organizar la lectura, limpieza, clasificación, consolidación y generación de reportes en módulos separados.	Las funciones principales están organizadas en módulos de código identificables.
RNF-06	Protección de datos	El sistema deberá proteger la información administrativa procesada.	Los archivos no se publican en repositorios públicos y se establece un manejo controlado de temporales.

