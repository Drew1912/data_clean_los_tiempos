-- Esquema vigente: usuarios con roles, datos de facturas y auditoria.
-- Identificadores UUID generados por la aplicación. Datos temporales con retención.
BEGIN;

-- Cuentas administradas con roles y sesion revocable.
CREATE SEQUENCE usuario_id_seq AS SMALLINT START WITH 2;
CREATE TABLE usuario (
    id SMALLINT PRIMARY KEY DEFAULT nextval('usuario_id_seq'),
    nombre TEXT NOT NULL UNIQUE,
    rol TEXT NOT NULL DEFAULT 'consulta' CHECK (rol IN ('administrador','cajas','contabilidad','consulta','descarga','carga')),
    password_hash TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    puede_ver_auditoria BOOLEAN NOT NULL DEFAULT FALSE,
    version_sesion INTEGER NOT NULL DEFAULT 0 CHECK (version_sesion >= 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER SEQUENCE usuario_id_seq OWNED BY usuario.id;
CREATE UNIQUE INDEX usuario_nombre_normalizado ON usuario(lower(nombre));

CREATE TABLE lote (
    id UUID PRIMARY KEY,
    creado_por SMALLINT REFERENCES usuario(id) ON DELETE RESTRICT,
    estado TEXT NOT NULL DEFAULT 'cargado'
        CHECK (estado IN ('cargado', 'procesando', 'completado', 'fallido', 'vencido')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    vence_en TIMESTAMPTZ NOT NULL,
    iniciado_en TIMESTAMPTZ,
    finalizado_en TIMESTAMPTZ,
    ultima_exportacion JSONB,
    CHECK (vence_en > creado_en),
    CHECK (finalizado_en IS NULL OR iniciado_en IS NOT NULL),
    CHECK (finalizado_en IS NULL OR finalizado_en >= iniciado_en)
);

CREATE TABLE archivo (
    id UUID PRIMARY KEY,
    lote_id UUID NOT NULL REFERENCES lote(id) ON DELETE CASCADE,
    posicion INTEGER NOT NULL CHECK (posicion >= 0),
    nombre_original TEXT NOT NULL,
    nombre_interno TEXT NOT NULL UNIQUE,
    extension TEXT NOT NULL,
    bytes BIGINT NOT NULL CHECK (bytes >= 0),
    sha256 TEXT NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    perfil_id TEXT,
    perfil_version TEXT,
    perfil_snapshot JSONB,
    estado TEXT NOT NULL CHECK (estado IN ('admitido', 'rechazado')),
    hojas JSONB NOT NULL DEFAULT '[]'::jsonb,
    UNIQUE (lote_id, posicion),
    CHECK (jsonb_typeof(hojas) = 'array'),
    CONSTRAINT archivo_admitido_perfil_check CHECK (estado <> 'admitido' OR
        (extension IN ('.xls', '.xlsx', '.csv') AND perfil_id IS NOT NULL AND
         perfil_version IS NOT NULL AND perfil_snapshot IS NOT NULL))
);

CREATE TABLE registro (
    id UUID PRIMARY KEY,
    archivo_id UUID NOT NULL REFERENCES archivo(id) ON DELETE CASCADE,
    hoja TEXT,
    fila INTEGER NOT NULL CHECK (fila > 0),
    linea_fin INTEGER CHECK (linea_fin >= fila),
    original JSONB NOT NULL,
    adicionales JSONB NOT NULL DEFAULT '{}'::jsonb,
    cambios JSONB NOT NULL DEFAULT '[]'::jsonb,
    numero_factura TEXT,
    fecha_factura DATE,
    nit_ci TEXT,
    modalidad_codigo TEXT,
    caja_codigo TEXT,
    monto_numeral NUMERIC,
    razon_social TEXT,
    cuf TEXT,
    anulado TEXT,
    modalidad TEXT CHECK (modalidad IN ('contado', 'credito')),
    departamento TEXT CHECK (departamento IN ('cochabamba', 'la_paz', 'santa_cruz')),
    estado TEXT NOT NULL CHECK (estado IN ('valido', 'observado')),
    UNIQUE (id, archivo_id),
    CHECK (hoja IS NULL OR hoja <> ''),
    CHECK (jsonb_typeof(original) = 'object'),
    CHECK (jsonb_typeof(adicionales) = 'object'),
    CHECK (jsonb_typeof(cambios) = 'array'),
    CONSTRAINT registro_valido_campos_check CHECK (estado <> 'valido' OR (
        NULLIF(BTRIM(numero_factura), '') IS NOT NULL AND
        fecha_factura IS NOT NULL AND
        NULLIF(BTRIM(nit_ci), '') IS NOT NULL AND
        modalidad_codigo IN ('C', 'P') AND modalidad_codigo IS NOT NULL AND
        monto_numeral IS NOT NULL AND
        modalidad IS NOT NULL
    )),
    CHECK (estado <> 'valido' OR
        (modalidad_codigo = 'C' AND modalidad = 'contado') OR
        (modalidad_codigo = 'P' AND modalidad = 'credito'))
);

-- COALESCE unifica el origen CSV sin exigir una versión particular de NULLS NOT DISTINCT.
CREATE UNIQUE INDEX registro_origen_unico
    ON registro (archivo_id, (COALESCE(hoja, '')), fila);

CREATE TABLE observacion (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    archivo_id UUID NOT NULL REFERENCES archivo(id) ON DELETE CASCADE,
    registro_id UUID,
    hoja TEXT,
    fila INTEGER CHECK (fila > 0),
    linea_fin INTEGER CHECK (linea_fin >= fila),
    campo TEXT,
    valor_original TEXT,
    tipo TEXT NOT NULL,
    motivo TEXT NOT NULL,
    grupo_candidato TEXT,
    regla TEXT,
    FOREIGN KEY (registro_id, archivo_id)
        REFERENCES registro(id, archivo_id) ON DELETE CASCADE,
    CHECK (registro_id IS NULL OR fila IS NOT NULL),
    CHECK (linea_fin IS NULL OR fila IS NOT NULL)
);

CREATE INDEX archivo_lote ON archivo(lote_id);
CREATE INDEX registro_filtros ON registro(archivo_id, estado, modalidad, departamento);
CREATE INDEX observacion_archivo ON observacion(archivo_id);
CREATE INDEX observacion_registro ON observacion(registro_id);
CREATE INDEX lote_vencimiento ON lote(vence_en);

CREATE TABLE auditoria (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ocurrido_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    usuario_id SMALLINT REFERENCES usuario(id) ON DELETE SET NULL,
    usuario_nombre TEXT NOT NULL CHECK (length(usuario_nombre) BETWEEN 1 AND 80),
    accion TEXT NOT NULL CHECK (accion IN ('ADMIN_CREADO','SESION_INICIADA','SESION_CERRADA','LOTE_CARGADO','CLASIFICACION_CONFIGURADA','LOTE_PROCESADO','COMPARACION_EJECUTADA','EXCEL_GENERADO','OBSERVACIONES_GENERADAS','LOTE_ELIMINADO','AUDITORIA_ACCESO','USUARIO_CREADO','USUARIO_ACTUALIZADO','USUARIOS_ACCESO')),
    resultado TEXT NOT NULL CHECK (resultado IN ('exito','rechazado','error')),
    lote_id UUID,
    detalles JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(detalles)='object')
);
CREATE INDEX auditoria_fecha ON auditoria(ocurrido_en DESC,id DESC);
CREATE INDEX auditoria_usuario ON auditoria(usuario_id,ocurrido_en DESC);
CREATE INDEX auditoria_lote ON auditoria(lote_id);

CREATE INDEX lote_autor_fecha ON lote(creado_por,creado_en DESC);
COMMIT;
