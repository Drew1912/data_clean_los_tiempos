-- Ampliación autorizada 2026-11-19: un administrador local; lotes previos sin autor.
CREATE TABLE IF NOT EXISTS usuario (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    nombre TEXT NOT NULL UNIQUE CHECK (nombre = 'admin'),
    password_hash TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    version_sesion INTEGER NOT NULL DEFAULT 0 CHECK (version_sesion >= 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE lote ADD COLUMN IF NOT EXISTS creado_por SMALLINT REFERENCES usuario(id) ON DELETE RESTRICT;
