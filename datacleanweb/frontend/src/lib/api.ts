export type EstadoSalud = { estado: "ok" | "error"; db: "ok" | "no_disponible" };
import type { Profile, Lot, Summary, Invoice, Observation, Page, Relation, CompareConfig, CompareResult } from "@/types/facturacion";
export type SessionUser = { id:number; nombre: string; rol:string; permisos:string[]; puede_ver_auditoria: boolean };
export type AuthSession = { usuario: SessionUser | null; csrf_token: string };
let csrf: string | null = null;

async function responseFor(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.method && !["GET", "HEAD"].includes(init.method)) {
    if (!csrf) await consultarSesion();
    headers.set("X-CSRF-Token", csrf ?? "");
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1/${path}`, { ...init, headers, credentials: "same-origin", cache: "no-store" });
  } catch {
    throw new Error("No se pudo conectar. Comprueba que la API esté iniciada.");
  }
  if (!response.ok) {
    let body;
    try { body = await response.json(); }
    catch { throw new Error("La API devolvió una respuesta inesperada. Comprueba el estado del lote."); }
    if (response.status === 401 && !path.startsWith("auth/")) {
      csrf = null;
      window.dispatchEvent(new Event("dataclean:sesion-vencida"));
    }
    throw new Error(body.error?.mensaje ?? "No se pudo completar la operación.");
  }
  return response;
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await responseFor(path, init);
  try { return await response.json() as T; }
  catch { throw new Error("La API devolvió una respuesta inesperada. Comprueba el estado del lote."); }
}

export async function descargarExcel(id: string, kind: "limpios" | "observaciones", modalidad = "todos", departamento = "todos") {
  const response = await responseFor(`lotes/${id}/exportaciones/${kind}`, { method: "POST",
    ...(kind === "limpios" ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ modalidad, departamento }) } : {}) });
  if (!(response.headers.get("Content-Type") ?? "").startsWith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")) throw new Error("No se recibió un archivo Excel válido. No se inició la descarga.");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = response.headers.get("Content-Disposition")?.match(/filename="([a-zA-Z0-9_.-]+)"/)?.[1] ?? `${kind}_${id}.xlsx`;
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60000);
}

export async function consultarSesion() {
  const result = await api<AuthSession>("auth/sesion"); csrf = result.csrf_token; return result;
}
export async function iniciarSesion(usuario: string, contrasena: string) {
  const result = await api<AuthSession>("auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario, contrasena }) });
  csrf = result.csrf_token; return result;
}
export async function cerrarSesion() {
  await api("auth/logout", { method: "POST" }); csrf = null;
}

export const consultarPerfiles = () => api<{ datos: Profile[] }>("perfiles");
export type ManagedUser = SessionUser & { activo:boolean; creado_en:string };
export type Role = { codigo:string; nombre:string; permisos:string[] };
export type UsersPage = Page<ManagedUser> & { roles:Role[] };
export const consultarUsuarios = (page=1) => api<UsersPage>(`usuarios?pagina=${page}&tamano=25`);
export const guardarUsuario = (data:Record<string,unknown>, id?:number) => api<ManagedUser>(id ? `usuarios/${id}` : 'usuarios', {method:id?'PATCH':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
export type SavedLot = { id:string; estado:string; creado_en:string; vence_en:string; usuario:string|null; archivos:number };
export const consultarCargas = (page=1) => api<Page<SavedLot>>(`lotes?pagina=${page}&tamano=10`);
export type AuditEvent = { id: string; ocurrido_en: string; usuario_nombre: string; accion: string; descripcion: string; resultado: string; lote_id: string | null; detalles: Record<string, string | number> };
export type AuditPage = Page<AuditEvent> & { acciones: { codigo: string; nombre: string }[] };
export const consultarAuditoria = (filters: Record<string, string>, page = 1) => api<AuditPage>(`auditoria?${new URLSearchParams({ ...filters, pagina: String(page), tamano: "25" })}`);
export const consultarLote = (id: string) => api<Lot>(`lotes/${id}`);
export const consultarResumen = (id: string, modalidad = "todos", departamento = "todos") => api<Summary>(`lotes/${id}/resumen?${new URLSearchParams({ modalidad, departamento })}`);
export const consultarRegistros = (id: string, page = 1, state = "todos", modalidad = "todos", departamento = "todos") => api<Page<Invoice>>(`lotes/${id}/registros?${new URLSearchParams({ pagina: String(page), tamano: "25", estado: state, modalidad, departamento })}`);
export const consultarRelaciones = (id: string, page = 1) => api<Page<Relation> & { sin_relacion: number; registros_evaluados: number }>(`lotes/${id}/relaciones?pagina=${page}&tamano=25`);
export const consultarObservaciones = (id: string, page = 1) => api<Page<Observation>>(`lotes/${id}/observaciones?pagina=${page}&tamano=25`);
export const procesarLote = (id: string, contratos?: { archivo_id: string; columna: string | null }[]) => api<Summary>(`lotes/${id}/procesamiento`, { method: "POST", ...(contratos ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ contratos }) } : {}) });
export const compararLote = (id: string, config: CompareConfig) => api<CompareResult>(`lotes/${id}/comparaciones`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) });
export function cargarLote(entries: { file: File; profileId: string }[], profiles: Profile[]) {
  const form = new FormData();
  entries.forEach(entry => form.append("archivos", entry.file));
  form.append("manifiesto", JSON.stringify({ archivos: entries.map((entry, indice) => ({
    indice, perfil_id: entry.profileId,
    perfil_version: profiles.find(profile => profile.id === entry.profileId)?.version ?? "1",
  })) }));
  return api<Lot>("lotes", { method: "POST", body: form });
}

export async function consultarSalud(): Promise<EstadoSalud> {
  const response = await fetch("/api/v1/health", { cache: "no-store" });
  if (!response.ok) throw new Error("La API o la base de datos no están disponibles.");
  const result: EstadoSalud = await response.json();
  if (result.estado !== "ok" || result.db !== "ok") throw new Error("Respuesta de salud inesperada.");
  return result;
}
