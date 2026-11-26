"use client";

import { useState, type ReactNode } from "react";
import { consultarSalud } from "@/lib/api";
import AuthGate from "./AuthGate";
import InvoiceWorkspace from "./InvoiceWorkspace";

export default function WorkspaceShell({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  async function checkConnection() {
    setBusy(true); setStatus("Comprobando conexión…");
    try { await consultarSalud(); setStatus("Conexión correcta: API y base de datos disponibles."); }
    catch (reason) { setStatus(reason instanceof Error ? reason.message : "No se pudo comprobar la conexión."); }
    finally { setBusy(false); }
  }
  return <AuthGate><main className="application-shell">
    <a className="skip-link" href="#workspace-heading">Ir al contenido</a>
    <header className="application-header">
      <div><span className="marca">LOS TIEMPOS</span><small>DataClean · Facturación</small></div>
      <div className="connection-tools"><button className="secondary" disabled={busy} onClick={() => void checkConnection()}>{busy ? "Comprobando…" : "Comprobar conexión"}</button><span role="status">{status}</span></div>
    </header>
    {children}
    <InvoiceWorkspace />
    <footer>Editorial Canelas S.A. · Entorno de desarrollo</footer>
  </main></AuthGate>;
}
