// El contenedor ya copia los estáticos; esta preparación es solo para ejecución local.
const { cpSync } = require("node:fs");
const { join, resolve } = require("node:path");
const buildDir = process.env.NEXT_DIST_DIR || ".next";
const standalone = join(buildDir, "standalone");
cpSync(join(buildDir, "static"), join(standalone, buildDir, "static"), { recursive: true });
cpSync("public", join(standalone, "public"), { recursive: true });
process.env.HOSTNAME = "127.0.0.1";
process.env.PORT ??= "3000";
require(resolve(standalone, "server.js"));
