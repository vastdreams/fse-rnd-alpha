-- Historical review/output rows are meaningful only in the immutable universe
-- that supplied their inputs. Existing versionless rows stay quarantined by
-- the read paths; all new rows must name a sealed build.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_ranked_rows_build'
           AND conrelid = 'ranked_rows'::regclass
    ) THEN
        ALTER TABLE ranked_rows
            ADD CONSTRAINT fk_ranked_rows_build
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_deepseek_audit_runs_build'
           AND conrelid = 'deepseek_audit_runs'::regclass
    ) THEN
        ALTER TABLE deepseek_audit_runs
            ADD CONSTRAINT fk_deepseek_audit_runs_build
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_final_reviews_build'
           AND conrelid = 'final_reviews'::regclass
    ) THEN
        ALTER TABLE final_reviews
            ADD CONSTRAINT fk_final_reviews_build
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_audit_trail_entries_build'
           AND conrelid = 'audit_trail_entries'::regclass
    ) THEN
        ALTER TABLE audit_trail_entries
            ADD CONSTRAINT fk_audit_trail_entries_build
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION require_versioned_historical_output()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.universe_version IS NULL OR NOT EXISTS (
            SELECT 1
              FROM universe_builds
             WHERE universe_version = NEW.universe_version
               AND status = 'sealed'
        ) THEN
            RAISE EXCEPTION
                '% requires a sealed universe version',
                TG_TABLE_NAME;
        END IF;
    ELSIF OLD.universe_version IS NULL THEN
        RAISE EXCEPTION
            'versionless legacy % is quarantined and cannot be modified',
            TG_TABLE_NAME;
    ELSIF NEW.universe_version IS DISTINCT FROM OLD.universe_version THEN
        RAISE EXCEPTION
            '% cannot be moved between immutable universe versions',
            TG_TABLE_NAME;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_deepseek_audit_runs_versioned ON deepseek_audit_runs;
CREATE TRIGGER trg_deepseek_audit_runs_versioned
BEFORE INSERT OR UPDATE ON deepseek_audit_runs
FOR EACH ROW EXECUTE FUNCTION require_versioned_historical_output();

DROP TRIGGER IF EXISTS trg_final_reviews_versioned ON final_reviews;
CREATE TRIGGER trg_final_reviews_versioned
BEFORE INSERT OR UPDATE ON final_reviews
FOR EACH ROW EXECUTE FUNCTION require_versioned_historical_output();

DROP TRIGGER IF EXISTS trg_audit_trail_entries_versioned ON audit_trail_entries;
CREATE TRIGGER trg_audit_trail_entries_versioned
BEFORE INSERT OR UPDATE ON audit_trail_entries
FOR EACH ROW EXECUTE FUNCTION require_versioned_historical_output();

-- Ranked rows are build content, not a mutable cache. A sealed build is
-- complete before it becomes visible, so late ranking writes would falsify a
-- historical result.
DROP TRIGGER IF EXISTS trg_ranked_rows_immutable ON ranked_rows;
CREATE TRIGGER trg_ranked_rows_immutable
BEFORE INSERT OR UPDATE OR DELETE ON ranked_rows
FOR EACH ROW EXECUTE FUNCTION reject_sealed_universe_content_mutation();
