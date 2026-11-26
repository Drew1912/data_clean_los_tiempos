export type Profile = { id: string; version: string; descripcion: string; extensiones: string[]; sintetico: boolean };
export type SourceFile = { id: string; indice: number; nombre: string; estado: "admitido" | "rechazado"; motivos: string[]; perfil_descripcion?: string; nivel?: string; columna_contrato?: string | null; hojas: { nombre: string | null; estado: string; nivel: string; mapeo?: Record<string,string>; columnas?: string[] }[] };
export type Lot = { lote_id: string; estado: string; archivos: SourceFile[]; advertencias: string[]; puede_procesar: boolean; vence_en: string };
export type Summary = { lote_id: string; estado: string; registros: { cargados: number | null; validos: number | null; observados: number | null; seleccionados: number | null; exportados: number | null }; cantidad_observaciones_fila: number; cantidad_observaciones_estructura: number; advertencias: string[]; ultima_exportacion: { cantidad: number; modalidad: string; departamento: string; generado_en: string } | null };
export type Origin = { archivo_id: string; archivo: string; hoja: string | null; fila: number | null; linea_fin: number | null };
export type RawCell = { valor: string; tipo: string; formato?: string; fecha_iso?: string };
export type Change = { campo: string; original: string; normalizado: string; regla: string };
export type Invoice = {
  nivel_registro?: string;
  id: string; numero_factura: string | null; fecha_factura: string | null; nit_ci: string | null;
  monto_numeral: string | null; razon_social: string | null; caja_codigo: string | null; modalidad_codigo: string | null;
  cuf: string | null; anulado: string | null; estado: string; modalidad: string | null; departamento: string | null;
  origen: Origin; cambios: Change[]; adicionales: Record<string, RawCell>;
  advertencias: { tipo: string; motivo: string; grupo_candidato: string | null }[];
};
export type Observation = { id: number; tipo: string; campo: string | null; motivo: string; valor_original: string | null; origen: Origin; registro_id: string | null; registro_original: Record<string, RawCell> | null; registro_normalizado: Partial<Invoice> | null; grupo_candidato: string | null };
export type Page<T> = { datos: T[]; pagina: number; tamano: number; total: number };
export type Relation = { id: string; tipo: string; estado: string; regla: string; facturas_originales: string[]; campos_diferentes: string[]; motivo: string; registros: Invoice[] };

export type CompareField = "nit_ci" | "monto_numeral";
export type CompareColumns = Record<CompareField | "numero_factura", string | null>;
export type CompareConfig = { archivo_base_id: string; archivos: { archivo_id: string; columnas: CompareColumns }[]; campos: CompareField[]; ignorar_ceros_factura: boolean; pagina?: number; tamano?: number; filtro?: string };
export type CompareValue = { original: string | null; valor: string | null; estado: string; motivo: string | null; valor_referencia?: string | null };
export type CompareResult = Page<{ numero_factura: string; estados: string[]; archivos: { archivo_id: string; estado: string; motivo: string; cantidad_encontrada: number; muestra_limitada: boolean; campos: Partial<Record<CompareField, CompareValue>>; registros: { id: string; origen: Origin; valores: Partial<Record<CompareField, CompareValue>> }[] }[] }> & {
  resumen: Record<string, number>; configuracion_id: string; configuracion: CompareConfig;
  archivos: { archivo_id: string; nombre: string; es_referencia: boolean; filas_sin_factura_comparable: number; filas_con_factura_comparable: number; columnas: CompareColumns }[];
  filas_sin_clave_muestra: { archivo_id: string; hoja: string | null; fila: number; motivo: string }[];
};
