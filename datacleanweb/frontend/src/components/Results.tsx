import type { Invoice, Observation, Origin, Page, Relation } from "@/types/facturacion";

function Source({ source }: { source: Origin }) {
  return <span className="source">{source.archivo}{source.hoja ? ` · ${source.hoja}` : ""}
    {source.fila ? ` · fila ${source.fila}${source.linea_fin && source.linea_fin !== source.fila ? `–${source.linea_fin}` : ""}` : " · archivo/hoja"}</span>;
}

export function Pager({ data, busy, change }: { data: Page<unknown>; busy: boolean; change: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(data.total / data.tamano));
  return <nav className="pager" aria-label="Paginación">
    <span>{data.total} {data.total === 1 ? "resultado" : "resultados"} · Página {data.pagina} de {pages}</span>
    <button className="secondary" disabled={busy || data.pagina <= 1} onClick={() => change(data.pagina - 1)}>Anterior</button>
    <button className="secondary" disabled={busy || data.pagina >= pages} onClick={() => change(data.pagina + 1)}>Siguiente</button>
  </nav>;
}

export function InvoiceTable({ data }: { data: Page<Invoice> }) {
  if (!data.total) return <p className="empty">No hay registros para este estado. Revisa los archivos y las observaciones.</p>;
  return <div className="table-scroll"><table><caption className="sr-only">Registros limpios con trazabilidad y cambios</caption>
    <thead><tr><th>Factura / nivel</th><th>Fecha</th><th>NIT/CI</th><th>Importe</th><th>Modalidad</th><th>Origen y cambios</th></tr></thead>
    <tbody>{data.datos.map(row => <tr key={row.id}>
      <td>{row.numero_factura ?? "—"}<small>{row.razon_social || "Sin razón social"}</small>
        <span className={`badge ${row.nivel_registro === "detalle" ? "notice" : row.estado === "valido" ? "accepted" : "rejected"}`}>{row.nivel_registro === "detalle" ? "Detalle" : row.estado === "valido" ? "Válido" : "Observado"}</span></td>
      <td>{row.fecha_factura ?? "—"}</td><td>{row.nit_ci ?? "—"}</td><td className="amount">{row.monto_numeral ?? "—"}</td>
      <td>{row.modalidad === "contado" ? "Contado" : row.modalidad === "credito" ? "Crédito" : "Sin clasificar"}</td>
      <td><Source source={row.origen} />
        <details><summary>Ver {row.cambios.length} cambios y datos complementarios</summary>
          {row.cambios.length > 0 && <ul>{row.cambios.map((change, index) => <li key={index}>
            {change.campo}: <code>{change.original}</code> → <code>{change.normalizado}</code>
          </li>)}</ul>}
          <p>CUF: <code>{row.cuf ?? "No informado"}</code><br />ANULADO: <code>{row.anulado ?? "No informado"}</code></p>
          {Object.entries(row.adicionales).map(([key, value]) => <p key={key}><b>{key}</b>: {value.valor}</p>)}
        </details>
        {row.advertencias.map((note, index) => <p className="warning-text" key={index}>{note.motivo}</p>)}
      </td>
    </tr>)}</tbody>
  </table></div>;
}

export function RelationsTable({ data }: { data: Page<Relation> }) {
  if (!data.total) return <p className="empty">No hay correspondencias con las claves disponibles. Carga juntos los archivos que quieras relacionar; no se emparejan solo por NIT, fecha e importe.</p>;
  return <div>{data.datos.map(group => <article className="relation" key={group.id}>
    <h3>Factura {group.facturas_originales.join(" / ")} · {group.tipo === "cabecera_detalle" ? "Cabecera y detalle" : "Entre cabeceras"}</h3>
    <span className="badge notice">{group.estado === "ambiguo" ? "Ambiguo: varias cabeceras posibles" : group.estado === "con_diferencias" ? "Correspondencia con diferencias" : "Correspondencia propuesta"}</span>
    <p>{group.regla}</p><p className="note">{group.motivo}</p>
    {group.campos_diferentes.length > 0 && <p>Campos diferentes: {group.campos_diferentes.join(", ")}</p>}
    <details><summary>Revisar {group.registros.length} registros conservados</summary>
      <div className="table-scroll"><table><thead><tr><th>Nivel</th><th>Factura</th><th>Fecha</th><th>NIT/CI</th><th>Importe</th><th>Origen</th></tr></thead>
        <tbody>{group.registros.map(row => <tr key={row.id}><td>{row.nivel_registro}</td><td>{row.numero_factura}</td><td>{row.fecha_factura ?? "—"}</td><td>{row.nit_ci ?? "—"}</td><td>{row.monto_numeral ?? "—"}</td><td><Source source={row.origen} /></td></tr>)}</tbody>
      </table></div>
    </details>
  </article>)}</div>;
}

export function ObservationTable({ data }: { data: Page<Observation> }) {
  if (!data.total) return <p className="empty">No se registraron observaciones en este lote.</p>;
  return <div className="table-scroll"><table><caption className="sr-only">Errores y avisos conservando el registro original</caption>
    <thead><tr><th>Origen</th><th>Campo</th><th>Motivo</th><th>Valor y contexto</th></tr></thead>
    <tbody>{data.datos.map(note => <tr key={note.id}>
      <td><Source source={note.origen} /></td><td>{note.campo ?? "Registro / estructura"}</td>
      <td><span className={note.tipo.startsWith("AVISO_") ? "badge notice" : "badge rejected"}>{note.tipo.startsWith("AVISO_") ? "Aviso · fila conservada" : "Observado"}</span>
        <p>{note.motivo}</p>{note.grupo_candidato && <small>Grupo: {note.grupo_candidato}</small>}</td>
      <td><code>{note.valor_original ?? "—"}</code>{note.registro_original && <details><summary>Ver original y normalizado</summary>
        <p>Los campos inválidos quedan sin valor normalizado.</p>
        <pre>{JSON.stringify({ original: note.registro_original, normalizado: note.registro_normalizado }, null, 2)}</pre>
      </details>}</td>
    </tr>)}</tbody>
  </table></div>;
}
