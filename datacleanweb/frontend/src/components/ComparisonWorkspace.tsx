"use client";

import { useState } from "react";
import type { CompareColumns, CompareConfig, CompareField, CompareResult, Lot } from "@/types/facturacion";
import { Pager } from "./Results";

const labels: Record<string, string> = { numero_factura: "Número de factura", nit_ci: "NIT/CI", monto_numeral: "Monto numeral",
  coincidencia: "Coincidencia exacta", diferencia: "Con diferencias", faltante: "Falta en algún archivo", incompleto: "Datos incompletos", ambiguo: "Varias filas",
  coincide: "Coincide", difiere: "Difiere", referencia: "Referencia", no_existe: "No encontrado", sin_columna_factura: "Sin columna de factura",
  igual: "Igual", diferente: "Diferente", sin_dato: "Sin dato", sin_columna: "Sin columna", invalido: "Dato no comparable",
  sin_referencia_unica: "Sin referencia única", referencia_incompleta: "Referencia incompleta" };

export default function ComparisonWorkspace({ lot, busy, compare }: { lot: Lot; busy: boolean; compare: (config: CompareConfig) => Promise<CompareResult> }) {
  const files = lot.archivos.filter(file => file.estado === "admitido");
  const [selected, setSelected] = useState(() => files.filter(file => file.nivel !== "detalle").map(file => file.id));
  const [base, setBase] = useState(() => files.find(file => file.nivel !== "detalle")?.id ?? "");
  const [columns, setColumns] = useState<Record<string, CompareColumns>>(() => Object.fromEntries(files.map(file => {
    const mapping = Object.assign({}, ...file.hojas.filter(sheet => sheet.estado === "admitida").map(sheet => sheet.mapeo ?? {}));
    return [file.id, { numero_factura: mapping.numero_factura ?? null, nit_ci: mapping.nit_ci ?? null, monto_numeral: mapping.monto_numeral ?? null }];
  })));
  const [fields, setFields] = useState<CompareField[]>(["nit_ci", "monto_numeral"]);
  const [zeros, setZeros] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState("");
  function changed() { setResult(null); setError(""); }
  async function run(config: CompareConfig) {
    setError("");
    try { setResult(await compare(config)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo comparar."); }
  }
  const config: CompareConfig = { archivo_base_id: base, archivos: selected.map(id => ({ archivo_id: id, columnas: columns[id] })), campos: fields, ignorar_ceros_factura: zeros };
  return <section className="panel" aria-labelledby="comparison-title">
    <p className="eyebrow">02 · COMPARACIÓN ENTRE ARCHIVOS</p><h2 id="comparison-title">Busca por factura y compara sus datos</h2>
    <p>El número de factura localiza el registro. Elige las columnas de cada archivo y los campos que deben coincidir exactamente con la referencia. La fecha no forma parte de la búsqueda.</p>
    <div className="comparison-files">{files.map(file => {
      const options = [...new Set(file.hojas.filter(sheet => sheet.estado === "admitida").flatMap(sheet => sheet.columnas ?? Object.values(sheet.mapeo ?? {})))];
      return <fieldset key={file.id} disabled={busy} className="comparison-file">
        <legend>{file.nombre}</legend>
        <label className="check-label"><input type="checkbox" checked={selected.includes(file.id)} onChange={event => {
          const next = event.target.checked ? [...selected, file.id] : selected.filter(id => id !== file.id);
          setSelected(next); if (!next.includes(base)) setBase(next[0] ?? ""); changed();
        }} />Incluir este archivo{file.nivel === "detalle" ? " (detalle: sin sumar importes)" : ""}</label>
        {(["numero_factura", "nit_ci", "monto_numeral"] as const).map(role => <label key={role}>{labels[role]}
          <select aria-label={`${labels[role]} de ${file.nombre}`} disabled={!selected.includes(file.id)} value={columns[file.id][role] ?? ""} onChange={event => {
            setColumns(current => ({ ...current, [file.id]: { ...current[file.id], [role]: event.target.value || null } })); changed();
          }}><option value="">No disponible / sin seleccionar</option>{options.map(name => <option key={name} value={name}>{name}</option>)}</select>
        </label>)}
      </fieldset>;
    })}</div>
    <label>Archivo de referencia<select aria-label="Archivo de referencia" disabled={busy} value={base} onChange={event => { setBase(event.target.value); changed(); }}>
      {!base && <option value="">Seleccionar referencia</option>}{files.filter(file => selected.includes(file.id)).map(file => <option key={file.id} value={file.id}>{file.nombre}</option>)}
    </select></label>
    <div className="comparison-options">{(["nit_ci", "monto_numeral"] as const).map(field => <label className="check-label" key={field}><input type="checkbox" disabled={busy} checked={fields.includes(field)} onChange={event => {
      setFields(event.target.checked ? [...fields, field] : fields.filter(item => item !== field)); changed();
    }} />Comparar {labels[field]}</label>)}
      <label className="check-label"><input type="checkbox" disabled={busy} checked={zeros} onChange={event => { setZeros(event.target.checked); changed(); }} />Ignorar ceros iniciales solo en el número de factura (001 = 1)</label>
    </div>
    <p className="note">Se conservan los ceros del NIT/CI. Los montos se comparan como decimales, sin redondeo. Las celdas vacías y las fórmulas no cuentan como coincidencia. Se incluyen también registros observados en la limpieza.</p>
    <button disabled={busy || selected.length < 2 || !fields.length || !base || !["cargado", "completado"].includes(lot.estado)} onClick={() => void run(config)}>Buscar facturas y comparar</button>
    {selected.length < 2 && <p>Incluye al menos dos archivos para comparar.</p>}
    {error && <p className="error-box" role="alert">{error}</p>}
    {result && <div aria-live="polite">
      <h3>Resultado por factura</h3><p>{result.resumen.facturas} números de factura encontrados entre todos los archivos seleccionados.</p>
      <div className="counters">{Object.entries(result.resumen).filter(([key]) => key !== "facturas").map(([key, value]) => <div key={key}><span>{labels[key]}</span><strong>{value}</strong></div>)}</div>
      <p className="note">Coincidencia exacta cuenta cada factura una sola vez cuando al menos otro archivo coincide con la referencia en todos los campos seleccionados. Esa misma factura puede faltar o diferir en otros archivos; los contadores y filtros pueden superponerse. Si aparece varias veces, se muestran sus filas sin elegir una ni sumar montos.</p>
      {result.archivos.filter(file => file.filas_sin_factura_comparable).map(file => <div className="info-box" key={file.archivo_id}>
        <b>{file.nombre}</b><p>Se pudieron buscar {file.filas_con_factura_comparable} filas con número de factura. Otras {file.filas_sin_factura_comparable} filas no tienen un número utilizable en la columna {file.columnas.numero_factura ?? "sin seleccionar"}. Este aviso se refiere a esas filas; sus originales se conservan.</p>
        <details><summary>Ver ubicación y motivo de las filas sin número utilizable</summary>
          <ul>{result.filas_sin_clave_muestra.filter(row => row.archivo_id === file.archivo_id).map(row => <li key={`${row.hoja}-${row.fila}`}>{row.hoja ?? "CSV"} · fila {row.fila}: {row.motivo}</li>)}</ul>
          <p>Se muestran hasta 100 ubicaciones por comparación. Revisa los registros para ver todas las filas o selecciona otra columna de factura si la actual no corresponde.</p>
        </details>
      </div>)}
      <label>Mostrar resultados<select aria-label="Filtrar comparación" disabled={busy} value={result.configuracion.filtro ?? "todos"} onChange={event => void run({ ...result.configuracion, filtro: event.target.value, pagina: 1 })}>
        <option value="todos">Todas las facturas</option>{["coincidencia", "diferencia", "faltante", "incompleto", "ambiguo"].map(key => <option key={key} value={key}>{labels[key]}</option>)}
      </select></label>
      {!result.total ? <p className="empty">No hay facturas con este filtro. Revisa las columnas y las filas sin clave si no se pudo buscar ningún registro.</p> : <div className="table-scroll"><table className="comparison-table">
        <caption className="sr-only">Comparación de NIT/CI y monto por factura y archivo</caption>
        <thead><tr><th>Factura</th>{result.archivos.map(file => <th key={file.archivo_id}>{file.nombre}{file.es_referencia && <small>Referencia</small>}</th>)}</tr></thead>
        <tbody>{result.datos.map(row => <tr key={row.numero_factura}><th scope="row">{row.numero_factura}</th>{row.archivos.map(cell => <td key={cell.archivo_id}>
          <b className={`badge ${cell.estado === "coincide" ? "accepted" : cell.estado === "referencia" ? "notice" : "rejected"}`}>{labels[cell.estado] ?? cell.estado}</b>
          <p>{cell.motivo}</p>{Object.entries(cell.campos).map(([field, value]) => <p key={field}><b>{labels[field]}:</b> {value?.original || "—"} · {labels[value?.estado ?? ""] ?? value?.estado}{value?.estado === "diferente" && <> (referencia: {value.valor_referencia})</>}</p>)}
          {!!cell.registros.length && <details><summary>Ver {cell.cantidad_encontrada} fila(s) de origen</summary>{cell.registros.map(record => <div key={record.id} className="comparison-origin"><b>{record.origen.hoja ?? "CSV"} · fila {record.origen.fila}</b>{Object.entries(record.valores).map(([field, value]) => <p key={field}>{labels[field]}: {value?.original || "—"}{value?.motivo && <> · {value.motivo}</>}</p>)}</div>)}{cell.muestra_limitada && <p>Se muestran las primeras 50 filas; todas se conservan en los registros.</p>}</details>}
        </td>)}</tr>)}</tbody>
      </table></div>}
      <Pager data={result} busy={busy} change={page => void run({ ...result.configuracion, pagina: page })} />
    </div>}
  </section>;
}
