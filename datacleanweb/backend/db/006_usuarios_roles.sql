BEGIN;
ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_id_check;
ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_nombre_check;
CREATE SEQUENCE IF NOT EXISTS usuario_id_seq AS SMALLINT START WITH 2;
ALTER SEQUENCE usuario_id_seq OWNED BY usuario.id;
ALTER TABLE usuario ALTER COLUMN id SET DEFAULT nextval('usuario_id_seq');
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='usuario'::regclass AND attname='rol' AND NOT attisdropped) THEN
        ALTER TABLE usuario ADD COLUMN rol TEXT NOT NULL DEFAULT 'consulta'
            CHECK (rol IN ('administrador','cajas','contabilidad','consulta','descarga','carga'));
        UPDATE usuario SET rol='administrador' WHERE id=1 AND nombre='admin';
    END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS usuario_nombre_normalizado ON usuario(lower(nombre));
ALTER TABLE auditoria DROP CONSTRAINT IF EXISTS auditoria_accion_check;
ALTER TABLE auditoria ADD CONSTRAINT auditoria_accion_check CHECK (accion IN (
    'ADMIN_CREADO','SESION_INICIADA','SESION_CERRADA','LOTE_CARGADO','CLASIFICACION_CONFIGURADA',
    'LOTE_PROCESADO','COMPARACION_EJECUTADA','EXCEL_GENERADO','OBSERVACIONES_GENERADAS',
    'LOTE_ELIMINADO','AUDITORIA_ACCESO','USUARIO_CREADO','USUARIO_ACTUALIZADO','USUARIOS_ACCESO'));
CREATE INDEX IF NOT EXISTS lote_autor_fecha ON lote(creado_por,creado_en DESC);
COMMIT;
