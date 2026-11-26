"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { consultarAuditoria, type AuditPage } from "@/lib/api";
import { useSessionUser } from "./AuthGate";
import { Pager } from "./Results";

const EMPTY: AuditPage = { datos:[], pagina:1, tamano:25, total:0, acciones:[] };
const FILTERS = { desde:"", hasta:"", accion:"", resultado:"", usuario:"", lote_id:"" };
const labels: Record<string, string> = { registros:"Registros", archivos:"Archivos", admitidos:"Admitidos", rechazados:"Rechazados", validos:"Válidos", observados:"Observados", cambios:"Normalizaciones", observaciones:"Incidencias", contratos:"Columnas de contrato seleccionadas", modalidad:"Modalidad", codigo:"Código de resultado", configuracion:"Referencia de configuración" };
const results: Record<string,string> = { exito:"Correcto", rechazado:"Rechazado", error:"Error" };

export default function AuditWorkspace({ active }: { active: boolean }) {
  const user = useSessionUser();
  const [filters,setFilters] = useState(FILTERS), [applied,setApplied] = useState(FILTERS);
  const [data,setData] = useState<AuditPage>(EMPTY), [busy,setBusy] = useState(false), [error,setError] = useState("");
  const sequence = useRef(0);
  async function load(next=applied,page=1) {
    const requestId=++sequence.current;setBusy(true);setError("");
    try { const loaded=await consultarAuditoria(next,page);if(requestId===sequence.current){setData(loaded);setApplied(next);} }
    catch(reason){if(requestId===sequence.current){setData(EMPTY);setError(reason instanceof Error?reason.message:"No se pudo consultar el historial.");}}
    finally{if(requestId===sequence.current)setBusy(false);}
  }
  useEffect(()=>{if(active&&user?.puede_ver_auditoria)void load();},[active,user?.puede_ver_auditoria]);
  if(!user?.puede_ver_auditoria)return <section className="panel"><h2>Acceso restringido</h2><p>Tu usuario no tiene permiso para consultar el historial de auditoría.</p></section>;
  function submit(event:FormEvent){event.preventDefault();void load(filters);}
  return <section className="panel" aria-labelledby="audit-title">
    <div className="panel-heading"><h2 id="audit-title">Historial de actividad</h2><button className="secondary" disabled={busy} onClick={()=>void load()}>Actualizar historial</button></div>
    <p>Ingresos, acciones y cambios del sistema. Fechas y filtros en horario de Bolivia.</p>
    <form className="audit-filters" onSubmit={submit}>
      <label>Desde<input type="date" aria-label="Auditoría desde" value={filters.desde} onChange={e=>setFilters({...filters,desde:e.target.value})} /></label>
      <label>Hasta<input type="date" aria-label="Auditoría hasta" value={filters.hasta} onChange={e=>setFilters({...filters,hasta:e.target.value})} /></label>
      <label>Acción<select aria-label="Filtrar acción de auditoría" value={filters.accion} onChange={e=>setFilters({...filters,accion:e.target.value})}><option value="">Todas</option>{data.acciones.map(action=><option key={action.codigo} value={action.codigo}>{action.nombre}</option>)}</select></label>
      <label>Resultado<select aria-label="Filtrar resultado de auditoría" value={filters.resultado} onChange={e=>setFilters({...filters,resultado:e.target.value})}><option value="">Todos</option>{Object.entries(results).map(([key,value])=><option key={key} value={key}>{value}</option>)}</select></label>
      <label>Usuario<input aria-label="Filtrar usuario de auditoría" maxLength={80} value={filters.usuario} placeholder="Ejemplo: admin" onChange={e=>setFilters({...filters,usuario:e.target.value})}/></label>
      <label>Lote<input aria-label="Filtrar lote de auditoría" value={filters.lote_id} placeholder="Identificador UUID" onChange={e=>setFilters({...filters,lote_id:e.target.value})}/></label>
      <div className="actions"><button disabled={busy} type="submit">Filtrar historial</button><button disabled={busy} type="button" className="secondary" onClick={()=>{setFilters(FILTERS);void load(FILTERS);}}>Limpiar filtros</button></div>
    </form>
    {busy&&<p role="status">Consultando historial…</p>}{error&&<p className="error-box" role="alert">{error}</p>}
    {!busy&&!error&&!data.total&&<p className="empty">No hay eventos para estos filtros. El historial registra actividad a partir de su instalación.</p>}
    {!!data.total&&<div className="table-scroll"><table className="audit-table"><caption className="sr-only">Eventos de auditoría, del más reciente al más antiguo</caption>
      <thead><tr><th>Fecha y hora</th><th>Usuario</th><th>Acción</th><th>Resultado</th><th>Referencia y detalle</th></tr></thead>
      <tbody>{data.datos.map(event=><tr key={event.id}>
        <td><time dateTime={event.ocurrido_en}>{new Date(event.ocurrido_en).toLocaleString("es-BO",{timeZone:"America/La_Paz"})}</time><small>Evento {event.id}</small></td>
        <td>{event.usuario_nombre}</td><td>{event.descripcion}</td><td><span className={`badge ${event.resultado==="exito"?"accepted":"rejected"}`}>{results[event.resultado]}</span></td>
        <td>{event.lote_id&&<p>Lote: <code>{event.lote_id}</code></p>}{Object.entries(event.detalles).map(([key,value])=><p key={key}>{labels[key]??key}: {String(value)}</p>)}</td>
      </tr>)}</tbody>
    </table></div>}
    <Pager data={data} busy={busy} change={page=>void load(applied,page)}/>
    <p className="note">El historial conserva acciones y cantidades, sin contraseñas ni valores de facturas. Las normalizaciones detalladas se consultan en los registros mientras el lote esté disponible. No se permite editar ni borrar eventos desde esta pantalla.</p>
  </section>;
}
