"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cargarLote, consultarLote, consultarObservaciones, consultarPerfiles, consultarRegistros, consultarResumen, procesarLote, compararLote, descargarExcel } from "@/lib/api";
import type { Invoice, Lot, Observation, Page, Profile, Summary, CompareConfig, CompareResult } from "@/types/facturacion";
import { InvoiceTable, ObservationTable, Pager } from "./Results";

import ComparisonWorkspace from "./ComparisonWorkspace";
import AuditWorkspace from "./AuditWorkspace";
import { useSessionUser } from "./AuthGate";
import UsersWorkspace from './UsersWorkspace';
import LotPicker from './LotPicker';

type Entry = { id: string; file: File; profileId: string };
const EMPTY = { datos: [], pagina: 1, tamano: 25, total: 0 };
const SECTIONS = [
  { path: "/importacion", title: "Importación", detail: "Archivos y contratos", description: "Carga los archivos y elige las columnas de contrato para clasificar Contado y Crédito." },
  { path: "/comparacion", title: "Comparación", detail: "Coincidencias por factura", description: "Busca por número de factura y compara NIT/CI y monto entre los archivos seleccionados." },
  { path: "/revision", title: "Revisión", detail: "Resultados y descargas", description: "Revisa los registros, filtra por modalidad y descarga el Excel limpio o las observaciones." },
  { path: "/auditoria", title: "Auditoría", detail: "Historial del sistema", description: "Consulta fechas, usuarios y acciones registradas. Acceso reservado a usuarios autorizados." },
  { path: '/usuarios', title: 'Usuarios', detail: 'Cuentas y permisos', description: 'Administra las cuentas y los permisos de acceso al sistema.' },
];

export default function InvoiceWorkspace() {
  const user = useSessionUser();
  const can = (permission:string) => !!user?.permisos.includes(permission);
  const sectionAllowed = (path:string) => path==='/usuarios'?can('usuarios'):path==='/auditoria'?can('auditoria'):path==='/revision'?can('consultar'):path==='/comparacion'?can('comparar'):can('cargar')||can('consultar');
  const pathname = usePathname();
  const router = useRouter();
  const active = SECTIONS.find(section => section.path === pathname) ?? SECTIONS[0];
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [lot, setLot] = useState<Lot | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [records, setRecords] = useState<Page<Invoice>>(EMPTY);
  const [notes, setNotes] = useState<Page<Observation>>(EMPTY);
  const [recordState, setRecordState] = useState("todos");
  const [modality, setModality] = useState("todos");
  const [contractColumns, setContractColumns] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<"validos" | "observaciones">("validos");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function loadProfiles() {
    setError("");
    try { setProfiles((await consultarPerfiles()).datos); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudieron consultar los perfiles."); }
  }
  useEffect(() => { void loadProfiles(); }, []);
  useEffect(() => {
    document.getElementById("workspace-heading")?.focus({ preventScroll: true });
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname]);

  function chooseFiles(files: FileList | null) {
    if (!files) return;
    const all = [...entries, ...Array.from(files).map(file => ({
      id: crypto.randomUUID(), file, profileId: "auto",
    }))];
    if (all.length > 10 || all.some(entry => entry.file.size > 10 * 1024 * 1024) || all.reduce((sum, entry) => sum + entry.file.size, 0) > 25 * 1024 * 1024) {
      setError("Máximo 10 archivos, 10 MiB por archivo y 25 MiB por lote.");
      return;
    }
    setEntries(all); setError(""); setStatus("");
  }

  async function refresh(id: string) {
    if(!can('consultar')) {setLot(await consultarLote(id));setSummary(null);setRecords(EMPTY);setNotes(EMPTY);return;}
    const [loaded, totals, observations] = await Promise.all([consultarLote(id), consultarResumen(id, modality), consultarObservaciones(id)]);
    setLot(loaded); setSummary(totals); setNotes(observations);
    if (loaded.estado === "completado") {
      setRecords(await consultarRegistros(id, 1, recordState, modality));
    }
    else setRecords(EMPTY);
    if (loaded.estado !== "completado") setTab("observaciones");
  }

  async function openLot(id:string) {
    await execute(async()=>{
      const loaded=await consultarLote(id);
      setEntries([]);setContractColumns(Object.fromEntries(loaded.archivos.map(file=>[file.id,file.columna_contrato??''])));
      setModality('todos');setRecordState('todos');setRecords(EMPTY);setNotes(EMPTY);setSummary(null);setLot(loaded);
      // refresh usa el filtro de la renderización actual; abrir empieza sin filtros.
      if(can('consultar')){
        const [totals,notes,rows]=await Promise.all([consultarResumen(id),consultarObservaciones(id),loaded.estado==='completado'?consultarRegistros(id):Promise.resolve(EMPTY)]);
        setSummary(totals);setNotes(notes);setRecords(rows);setTab(loaded.estado==='completado'?'validos':'observaciones');
      }
      setStatus('Carga recuperada.');
    });
  }

  async function execute(action: () => Promise<void>) {
    setBusy(true); setError("");
    try { await action(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo completar la operación."); setStatus(""); }
    finally { setBusy(false); }
  }

  function upload() {
    void execute(async () => {
      setStatus("Leyendo archivos y validando su estructura…");
      const loaded = await cargarLote(entries, profiles);
      setLot(loaded);
      setContractColumns(Object.fromEntries(loaded.archivos.map(file => [file.id, file.columna_contrato ?? ""])));
      await refresh(loaded.lote_id);
      setStatus(!can('procesar')?'Archivos guardados. Tu rol permite cargar, pero no ejecutar limpieza.':loaded.puede_procesar ? "Carga lista. Elige las columnas de cada archivo y pulsa Buscar facturas y comparar." : "La carga no contiene cabeceras admitidas. Revisa los motivos y prepara una nueva carga.");
    });
  }

  function handleProcess() {
    if (!lot) return;
    void execute(async () => {
      setStatus("Limpiando y validando. Se conservarán las filas originales…");
      await procesarLote(lot.lote_id, classification());
      await refresh(lot.lote_id);
      setTab("validos");
      setStatus("Procesamiento terminado. Revisa los registros válidos y las observaciones.");
      router.push("/revision");
    });
  }

  async function handleCompare(config: CompareConfig): Promise<CompareResult> {
    if (!lot) throw new Error("Primero carga los archivos.");
    setBusy(true); setError(""); setStatus("Buscando facturas y comparando las columnas seleccionadas…");
    try {
      if (lot.estado === "cargado") {
        if(!can('procesar'))throw new Error('La carga todavía necesita limpieza. Tu rol no permite procesarla.');
        await procesarLote(lot.lote_id, classification()); await refresh(lot.lote_id);
      }
      const result = await compararLote(lot.lote_id, config);
      setStatus("Comparación terminada. Revisa el resultado por factura y archivo.");
      return result;
    } catch (reason) { setStatus(""); throw reason; }
    finally { setBusy(false); }
  }

  function newLot() {
    setModality("todos"); setContractColumns({});
    setLot(null); setSummary(null); setRecords(EMPTY); setNotes(EMPTY); setRecordState("todos"); setEntries([]); setError(""); setStatus("");
    router.push("/importacion");
  }

  function changePage(page: number) {
    if (!lot) return;
    void execute(async () => {
      if (tab === "validos") setRecords(await consultarRegistros(lot.lote_id, page, recordState, modality));
      else setNotes(await consultarObservaciones(lot.lote_id, page));
    });
  }

  function classification() {
    return lot?.archivos.filter(file => file.estado === "admitido").map(file => ({ archivo_id: file.id, columna: contractColumns[file.id] || null })) ?? [];
  }

  function filterRecords(nextModality: string) {
    if (!lot) return;
    void execute(async () => {
      const [rows, totals] = await Promise.all([consultarRegistros(lot.lote_id, 1, recordState, nextModality), consultarResumen(lot.lote_id, nextModality)]);
      setModality(nextModality); setRecords(rows); setSummary(totals);
    });
  }

  function download(kind: "limpios" | "observaciones") {
    if (!lot) return;
    void execute(async () => {
      setStatus("Generando el archivo Excel completo…");
      await descargarExcel(lot.lote_id, kind, modality);
      setStatus("Archivo generado; se solicitó la descarga al navegador.");
      setSummary(await consultarResumen(lot.lote_id, modality));
    });
  }

  return <div className="workspace-layout">
    <aside className="workspace-sidebar">
      <p className="sidebar-label">ÁREA DE TRABAJO</p>
      <nav aria-label="Navegación principal">{SECTIONS.filter(section=>sectionAllowed(section.path)).map((section, index) => <Link key={section.path} href={section.path} aria-current={active.path === section.path ? "page" : undefined}>
        <span className="nav-number" aria-hidden="true">0{index + 1}</span><span>{section.title}<small>{section.detail}</small></span>
      </Link>)}</nav>
      <div className="sidebar-lot"><b>{lot ? "Carga actual" : "Sin archivos cargados"}</b>
        <p>{lot ? `${lot.archivos.length} archivos · ${lot.estado}` : "Empieza por Importación para cargar tus documentos."}</p>
        {lot && <button className="secondary" disabled={busy} onClick={newLot}>Nueva carga</button>}
      </div>
    </aside>
    <div className="workspace-content">
      <div className="workspace-title"><p className="eyebrow">DATACLEAN</p><h1 id="workspace-heading" tabIndex={-1}>{active.title}</h1><p>{active.description}</p></div>
      {(status || error) && <div className="workspace-messages"><p className="workflow-status" role="status" aria-live="polite">{status}</p>{error && <div className="error-box" role="alert">{error}</div>}</div>}
      {!sectionAllowed(pathname)&&<section className="panel"><h2>Acceso restringido</h2><p>Tu rol no tiene permiso para acceder a este apartado.</p><Link href="/importacion">Ver mis cargas</Link></section>}
      <div className="workspace-page" hidden={pathname !== "/importacion"||!sectionAllowed('/importacion')}>
    <LotPicker active={pathname==='/importacion'&&sectionAllowed('/importacion')} busy={busy} open={openLot} revision={lot?.archivos.length??0}/>
    <section className="panel upload-panel" aria-labelledby="upload-title">
      <div className="panel-heading"><div><p className="eyebrow">01 · IMPORTACIÓN</p><h2 id="upload-title">Carga tus archivos</h2></div>
        {lot && <button className="secondary" disabled={busy} onClick={newLot}>Nueva carga</button>}
      </div>
      <p>Excel .xls / .xlsx o CSV · hasta 10 archivos · 10 MiB por archivo · 25 MiB por lote.</p>
      <div className="examples">Prueba con datos ficticios:
        <a href="/ejemplo_facturas.csv" download>CSV de ejemplo</a>
        <a href="/ejemplo_facturas_f1.xlsx" download>Excel · fila 1</a>
        <a href="/ejemplo_facturas_f4.xlsx" download>Excel · fila 4</a>
      </div>
      {!lot && can('cargar') && <label className="file-picker">Seleccionar archivos
        <input aria-label="Seleccionar archivos" type="file" accept=".xls,.xlsx,.csv" multiple disabled={busy || !profiles.length}
          onChange={event => { chooseFiles(event.currentTarget.files); event.currentTarget.value = ""; }} />
      </label>}
      {!profiles.length && <button className="secondary" onClick={() => void loadProfiles()}>Reintentar conexión con los perfiles</button>}
      {entries.length > 0 && !lot && <ul className="file-list">{entries.map(entry => <li key={entry.id}>
        <div className="file-name"><strong>{entry.file.name}</strong><small>{(entry.file.size / 1024).toFixed(1)} KiB</small></div>
        <label>Formato de lectura<select aria-label={`Formato de ${entry.file.name}`} disabled={busy} value={entry.profileId}
          onChange={event => setEntries(current => current.map(item => item.id === entry.id ? { ...item, profileId: event.target.value } : item))}>
          {profiles.map(profile => <option key={profile.id} value={profile.id}>{profile.descripcion}</option>)}
        </select></label>
        <button className="secondary" disabled={busy} onClick={() => setEntries(current => current.filter(item => item.id !== entry.id))} aria-label={`Quitar ${entry.file.name}`}>Quitar</button>
      </li>)}</ul>}
      {!lot && can('cargar') && <button disabled={busy || !entries.length || !profiles.length} onClick={upload}>1. Cargar archivos</button>}
      {!lot&&!can('cargar')&&<p className="info-box">Tu rol permite consultar cargas propias anteriores. No permite importar archivos nuevos.</p>}
      {lot && <>
        <p className="lot-label">Lote <code>{lot.lote_id}</code> · {lot.estado}</p>
        <ul className="loaded-files">{lot.archivos.map(file => <li key={file.id}>
          <b>{file.nombre}</b><span className={`badge ${file.estado === "admitido" ? "accepted" : "rejected"}`}>{file.estado}</span>
          <small>{file.perfil_descripcion ?? "Formato no identificado"} · {file.nivel ?? "sin nivel"}</small>
          {file.hojas.map((sheet, index) => sheet.mapeo && <details key={index}><summary>Correspondencia de columnas · {sheet.nombre ?? "CSV"}</summary>
            {Object.entries(sheet.mapeo).map(([canonical, original]) => <p key={canonical}><code>{original}</code> → <code>{canonical}</code></p>)}</details>)}
          {file.motivos.map((reason, index) => <p key={index}>{reason}</p>)}
          {file.estado === "admitido" && <label className="contract-picker">Columna de contrato para Contado/Crédito
            <select aria-label={`Contrato de ${file.nombre}`} disabled={busy || !can('procesar') || lot.estado !== "cargado"} value={contractColumns[file.id] ?? ""} onChange={event => setContractColumns(current => ({ ...current, [file.id]: event.target.value }))}>
              <option value="">Sin contrato: usar columna C/P si existe</option>
              {[...new Set(file.hojas.filter(sheet => sheet.estado === "admitida").flatMap(sheet => sheet.columnas ?? []))].map(column => <option key={column} value={column}>{column}</option>)}
            </select>
            <small>El contrato seleccionado debe empezar por C (Contado) o P (Crédito). Selección fija al procesar; para cambiarla crea una carga nueva.</small>
            {!contractColumns[file.id] && file.nivel !== "detalle" && !file.hojas.some(sheet => sheet.mapeo?.modalidad_codigo) && <small className="warning-text">Sin contrato elegido ni columna C/P, la modalidad quedará sin clasificar. Podrás comparar sus datos, pero esas filas no entrarán como válidas al Excel limpio.</small>}
          </label>}
        </li>)}</ul>
        <div className="actions">{can('procesar')&&<button disabled={busy || !lot.puede_procesar} onClick={handleProcess}>Limpiar y revisar registros</button>}
          <button className="secondary" disabled={busy} onClick={() => void execute(async () => { await refresh(lot.lote_id); setStatus("Estado actualizado."); })}>Actualizar estado</button>
        </div>
      </>}
      {lot && <p className="note">Elige la columna de contrato de cada archivo antes de limpiar o comparar. El departamento no se utiliza ni se exige. Un contrato vacío, fórmula o prefijo distinto de C/P queda observado.</p>}
      {lot && <div className="actions stage-navigation">{can('comparar')&&<Link className="action-link" href="/comparacion">Continuar a Comparación</Link>}{can('consultar')&&<Link className="action-link secondary" href="/revision">Ir a Revisión</Link>}</div>}
    </section>
      </div>
      <div className="workspace-page" hidden={pathname !== "/comparacion"||!can('comparar')}>
        {!lot ? <section className="panel empty-stage"><h2>Primero carga tus archivos</h2><p>Importa dos o más archivos para seleccionar columnas y comparar facturas.</p><Link className="action-link" href="/importacion">Ir a Importación</Link></section> : <>
          {lot.estado === "cargado" && <p className="info-box">Antes de comparar, revisa la columna de contrato elegida en <Link href="/importacion">Importación</Link>. La clasificación queda fija al procesar.</p>}
          <ComparisonWorkspace key={lot.lote_id} lot={lot} busy={busy} compare={handleCompare} />
          <div className="stage-navigation"><Link className="action-link secondary" href="/revision">Revisar resultados y descargar</Link></div>
        </>}
      </div>
      <div className="workspace-page" hidden={pathname !== "/revision"||!can('consultar')}>
        {!lot && <section className="panel empty-stage"><h2>Todavía no hay resultados</h2><p>Carga archivos para revisar sus registros y observaciones.</p><Link className="action-link" href="/importacion">Ir a Importación</Link></section>}
        {lot && lot.estado === "cargado" && <div className="info-box"><p>La carga está lista. Puedes revisar las observaciones de estructura o limpiar los registros para habilitar filtros y Excel limpio.</p>{can('procesar')&&<button disabled={busy || !lot.puede_procesar} onClick={handleProcess}>Limpiar y revisar registros</button>}<p><Link href="/importacion">Revisar columnas de contrato</Link></p></div>}
    {summary && <section className="panel" aria-labelledby="results-title">
      <div className="panel-heading"><div><p className="eyebrow">03 · REVISIÓN</p><h2 id="results-title">Resultado de la limpieza</h2></div></div>
      <div className="counters">{([ ["Cargados", summary.registros.cargados], ["Válidos", summary.registros.validos], ["Observados", summary.registros.observados], ["Válidos seleccionados", summary.registros.seleccionados], ["Exportados en el último Excel limpio", summary.registros.exportados] ] as const).map(([label, value]) => <div key={label}><span>{label}</span><strong>{value ?? "—"}</strong></div>)}</div>
      <div className="export-filters">
        <label>Modalidad<select aria-label="Filtrar modalidad" value={modality} disabled={busy || lot?.estado !== "completado"} onChange={event => filterRecords(event.target.value)}><option value="todos">Todos</option><option value="contado">Contado</option><option value="credito">Crédito</option></select></label>
      </div>
      {can('descargar')&&<div className="actions">
        <button disabled={busy || lot?.estado !== "completado"} onClick={() => download("limpios")}>Descargar Excel limpio</button>
        <button className="secondary" disabled={busy || lot?.estado === "procesando"} onClick={() => download("observaciones")}>Descargar observaciones</button>
      </div>}
      <p className="note">El Excel limpio incluye todos los válidos seleccionados, aunque en pantalla estés viendo observados u otra página. Sin coincidencias, contiene encabezados y contexto. Las observaciones abarcan todo el lote y la comparación mantiene sus propios criterios.</p>
      {summary.ultima_exportacion && <p className="note">Último Excel limpio: {summary.ultima_exportacion.cantidad} registros · {summary.ultima_exportacion.modalidad} · {new Date(summary.ultima_exportacion.generado_en).toLocaleString("es-BO", { timeZone: "America/La_Paz" })}. El contador acredita generación, no confirma la recepción en el equipo.</p>}
      <p className="note">Los observados incluyen campos faltantes y detalles no consolidables como factura. Se muestran todos los registros por defecto; no se pierden líneas ni se infiere clasificación por el nombre del archivo.</p>
      <div className="tabs" aria-label="Vistas de resultados">
        <button aria-pressed={tab === "validos"} disabled={busy || lot?.estado !== "completado"} onClick={() => setTab("validos")}>Registros leídos ({summary.registros.cargados ?? "—"})</button>
        <button aria-pressed={tab === "observaciones"} disabled={busy} onClick={() => setTab("observaciones")}>Observaciones ({notes.total})</button>
      </div>
      {tab === "validos" && <label className="state-filter">Mostrar <select value={recordState} disabled={busy} onChange={event => {
        const value = event.target.value; setRecordState(value);
        if (lot) void execute(async () => setRecords(await consultarRegistros(lot.lote_id, 1, value, modality)));
      }}><option value="todos">Todos los registros</option><option value="valido">Solo válidos</option><option value="observado">Observados y detalles</option></select></label>}
      {tab === "validos" ? <InvoiceTable data={records} /> : <ObservationTable data={notes} />}
      <Pager data={tab === "validos" ? records : notes} busy={busy} change={changePage} />
      <p className="note">Las observaciones permanecen completas al cambiar modalidad. No se asigna modalidad por el nombre del archivo ni se exige departamento.</p>
    </section>}
      </div>
      <div className="workspace-page" hidden={pathname !== "/auditoria"||!can('auditoria')}><AuditWorkspace active={pathname === "/auditoria"&&can('auditoria')}/></div>
      <div className="workspace-page" hidden={pathname !== '/usuarios'||!can('usuarios')}><UsersWorkspace active={pathname==='/usuarios'&&can('usuarios')}/></div>
    </div>
  </div>;
}
