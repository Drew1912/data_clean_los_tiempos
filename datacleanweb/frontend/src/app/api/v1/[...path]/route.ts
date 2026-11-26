import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
const MAX_REQUEST = 26 * 1024 * 1024;
const LOT = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const GET_PATH = new RegExp(`^(auth/sesion|perfiles|auditoria|usuarios|lotes|lotes/${LOT}(/(resumen|registros|observaciones|relaciones))?)$`, "i");
const POST_PATH = new RegExp(`^(auth/(login|logout)|usuarios|lotes|lotes/${LOT}/(procesamiento|comparaciones|exportaciones/(limpios|observaciones)))$`, "i");
const PATCH_PATH = /^usuarios\/[1-9][0-9]{0,4}$/;

async function forward(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const route = path.join("/");
  if (!(request.method === "GET" ? GET_PATH : request.method === "PATCH" ? PATCH_PATH : POST_PATH).test(route)) {
    return NextResponse.json({ error: { mensaje: "Recurso no disponible" } }, { status: 404 });
  }
  let body: Buffer | undefined;
  if (["POST", "PATCH"].includes(request.method) && request.body) {
    const reader = request.body.getReader();
    const chunks: Uint8Array[] = [];
    let bytes = 0;
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.byteLength;
      if (bytes > MAX_REQUEST) {
        await reader.cancel();
        return NextResponse.json({ error: { mensaje: "La petición supera el tamaño permitido" } }, { status: 413 });
      }
      chunks.push(chunk.value);
    }
    body = Buffer.concat(chunks);
  }
  try {
    const url = new URL(`/api/v1/${route}`, process.env.BACKEND_URL ?? "http://127.0.0.1:8000");
    url.search = new URL(request.url).search;
    const headers = new Headers({ Accept: "application/json" });
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("Content-Type", contentType);
    for (const name of ["cookie", "x-csrf-token"]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    const upstream = await fetch(url, { method: request.method, headers,
      body: body ? new Uint8Array(body).buffer : undefined,
      cache: "no-store", signal: AbortSignal.timeout(90000) });
    const responseHeaders = new Headers({
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      "Cache-Control": "no-store",
    });
    for (const name of ["Content-Disposition", "X-Registros-Exportados", "X-Observaciones-Exportadas"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    for (const cookie of upstream.headers.getSetCookie()) responseHeaders.append("Set-Cookie", cookie);
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return NextResponse.json({ error: { mensaje: "La API no respondió. Comprueba su conexión y el estado del lote antes de repetir." } }, { status: 503 });
  }
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
