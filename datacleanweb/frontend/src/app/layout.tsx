import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DataClean · Los Tiempos",
  description: "Carga y limpieza de registros de facturación con trazabilidad",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
