-- Permiso inicial solo al administrador existente, sin restablecer revocaciones.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='usuario'::regclass AND attname='puede_ver_auditoria' AND NOT attisdropped) THEN
        ALTER TABLE usuario ADD COLUMN puede_ver_auditoria BOOLEAN NOT NULL DEFAULT FALSE;
        UPDATE usuario SET puede_ver_auditoria=TRUE WHERE id=1 AND nombre='admin';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS auditoria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ocurrido_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    usuario_id SMALLINT REFERENCES usuario(id) ON DELETE SET NULL,
    usuario_nombre TEXT NOT NULL CHECK (length(usuario_nombre) BETWEEN 1 AND 80),
    accion TEXT NOT NULL CHECK (accion IN ('ADMIN_CREADO','SESION_INICIADA','SESION_CERRADA','LOTE_CARGADO','CLASIFICACION_CONFIGURADA','LOTE_PROCESADO','COMPARACION_EJECUTADA','EXCEL_GENERADO','OBSERVACIONES_GENERADAS','LOTE_ELIMINADO','AUDITORIA_ACCESO')),
    resultado TEXT NOT NULL CHECK (resultado IN ('exito','rechazado','error')),
    lote_id UUID,
    detalles JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(detalles)='object')
);
-- lote_id no lleva FK: la purga de lotes no debe eliminar su historial.
CREATE INDEX IF NOT EXISTS auditoria_fecha ON auditoria(ocurrido_en DESC,id DESC);
CREATE INDEX IF NOT EXISTS auditoria_usuario ON auditoria(usuario_id,ocurrido_en DESC);
CREATE INDEX IF NOT EXISTS auditoria_lote ON auditoria(lote_id);
