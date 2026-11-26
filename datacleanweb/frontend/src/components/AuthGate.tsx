"use client";

import { createContext, useContext, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { cerrarSesion, consultarSesion, iniciarSesion, type SessionUser } from "@/lib/api";

const SessionContext = createContext<SessionUser | null>(null);
export const useSessionUser = () => useContext(SessionContext);

export default function AuthGate({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);

  async function restore() {
    setBusy(true); setError("");
    try { const session = await consultarSesion(); setUser(session.usuario); setReady(true); }
    catch { setError("No se pudo conectar con el servicio de acceso. Comprueba que Flask esté iniciado y pulsa Reintentar conexión."); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    void restore();
    function expired() { setUser(null); setError("Tu sesión terminó. Inicia sesión para continuar."); }
    window.addEventListener("dataclean:sesion-vencida", expired);
    return () => window.removeEventListener("dataclean:sesion-vencida", expired);
  }, []);

  async function login(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { const session = await iniciarSesion(username, password); setPassword(""); setUser(session.usuario); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo iniciar sesión."); }
    finally { setBusy(false); }
  }
  async function logout() {
    setBusy(true); setError("");
    try { await cerrarSesion(); setUser(null); setUsername(""); setPassword(""); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo cerrar la sesión. Inténtalo de nuevo."); }
    finally { setBusy(false); }
  }
  if (user) return <SessionContext.Provider value={user}>
    <div className="session-toolbar"><span>Sesión: <b>{user.nombre}</b></span><button className="secondary" disabled={busy} onClick={() => void logout()}>Cerrar sesión</button>{error && <p role="alert">{error}</p>}</div>
    {children}
  </SessionContext.Provider>;
  return <main className="login-page">
    <header><span className="marca">LOS TIEMPOS</span><span className="etapa">DataClean · Acceso al sistema</span></header>
    <section className="panel login-panel" aria-labelledby="login-title">
      <p className="eyebrow">ACCESO AL SISTEMA</p><h1 id="login-title">Inicia sesión</h1>
      <p>Ingresa para cargar tus archivos y revisar las coincidencias entre facturas.</p>
      {!ready && !error && <p role="status">Comprobando sesión…</p>}
      <form onSubmit={event => void login(event)}>
        <label htmlFor="login-user">Usuario</label><input id="login-user" name="usuario" autoComplete="username" required maxLength={200} disabled={busy || !ready} value={username} onChange={event => setUsername(event.target.value)} />
        <label htmlFor="login-password">Contraseña</label><input id="login-password" name="contrasena" type={visible ? "text" : "password"} autoComplete="current-password" required maxLength={200} disabled={busy || !ready} value={password} onChange={event => setPassword(event.target.value)} />
        <label className="check-label"><input type="checkbox" checked={visible} onChange={event => setVisible(event.target.checked)} />Mostrar contraseña</label>
        <button type="submit" disabled={busy || !ready}>{busy ? "Conectando…" : "Ingresar"}</button>
      </form>
      {error && <p className="error-box" role="alert">{error}</p>}
      {!ready && error && <button className="secondary" disabled={busy} onClick={() => void restore()}>Reintentar conexión</button>}
      <p className="note">Utiliza la cuenta asignada por el administrador. Si necesitas acceso o recuperar tu contraseña, comunícate con él.</p>
    </section>
    <footer>Editorial Canelas S.A. · Prototipo académico local</footer>
  </main>;
}
