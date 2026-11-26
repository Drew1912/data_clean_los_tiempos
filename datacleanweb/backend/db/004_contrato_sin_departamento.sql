-- Regla autorizada: contrato C/P; departamento y caja dejan de bloquear válidos.
-- Mantiene columnas, datos previos y coherencia C/P -> modalidad.
DO $$
DECLARE candidate RECORD;
BEGIN
    FOR candidate IN SELECT conname FROM pg_constraint
        WHERE conrelid='registro'::regclass AND contype='c'
          AND pg_get_constraintdef(oid) LIKE '%fecha_factura%'
          AND pg_get_constraintdef(oid) LIKE '%caja_codigo%'
          AND pg_get_constraintdef(oid) LIKE '%valido%'
    LOOP
        EXECUTE format('ALTER TABLE registro DROP CONSTRAINT %I', candidate.conname);
    END LOOP;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='registro'::regclass AND conname='registro_valido_campos_check') THEN
        ALTER TABLE registro ADD CONSTRAINT registro_valido_campos_check CHECK (estado <> 'valido' OR (
            NULLIF(BTRIM(numero_factura),'') IS NOT NULL AND fecha_factura IS NOT NULL
            AND NULLIF(BTRIM(nit_ci),'') IS NOT NULL AND modalidad_codigo IN ('C','P') AND modalidad_codigo IS NOT NULL
            AND monto_numeral IS NOT NULL AND modalidad IS NOT NULL));
    END IF;
END $$;
