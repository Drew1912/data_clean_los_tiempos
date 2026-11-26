-- Ampliación autorizada: .xls. Sin tablas nuevas, sin modificar registros existentes.
BEGIN;
DO $$
DECLARE item RECORD;
BEGIN
    FOR item IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'archivo'::regclass AND contype = 'c'
          AND pg_get_constraintdef(oid) LIKE '%extension%'
          AND pg_get_constraintdef(oid) LIKE '%perfil_snapshot%'
    LOOP
        EXECUTE format('ALTER TABLE archivo DROP CONSTRAINT %I', item.conname);
    END LOOP;
    ALTER TABLE archivo ADD CONSTRAINT archivo_admitido_perfil_check
      CHECK (estado <> 'admitido' OR
        (extension IN ('.xls', '.xlsx', '.csv') AND perfil_id IS NOT NULL
         AND perfil_version IS NOT NULL AND perfil_snapshot IS NOT NULL));
END $$;
COMMIT;
