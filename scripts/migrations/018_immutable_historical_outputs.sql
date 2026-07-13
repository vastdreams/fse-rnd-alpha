-- Historical review and audit outputs are append-only evidence. An operator
-- may add a newly completed output to a sealed universe, but may never alter
-- or erase a recorded output after it has been written.

DROP TRIGGER IF EXISTS trg_deepseek_audit_runs_versioned ON deepseek_audit_runs;
CREATE TRIGGER trg_deepseek_audit_runs_versioned
BEFORE INSERT ON deepseek_audit_runs
FOR EACH ROW EXECUTE FUNCTION require_versioned_historical_output();

DROP TRIGGER IF EXISTS trg_final_reviews_versioned ON final_reviews;
CREATE TRIGGER trg_final_reviews_versioned
BEFORE INSERT ON final_reviews
FOR EACH ROW EXECUTE FUNCTION require_versioned_historical_output();

DROP TRIGGER IF EXISTS trg_audit_trail_entries_versioned ON audit_trail_entries;
CREATE TRIGGER trg_audit_trail_entries_versioned
BEFORE INSERT ON audit_trail_entries
FOR EACH ROW EXECUTE FUNCTION require_versioned_historical_output();

CREATE OR REPLACE FUNCTION reject_historical_output_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        '% records are append-only and cannot be % after being recorded',
        TG_TABLE_NAME,
        LOWER(TG_OP);
END $$;

DROP TRIGGER IF EXISTS trg_deepseek_audit_runs_append_only ON deepseek_audit_runs;
CREATE TRIGGER trg_deepseek_audit_runs_append_only
BEFORE UPDATE OR DELETE ON deepseek_audit_runs
FOR EACH ROW EXECUTE FUNCTION reject_historical_output_mutation();

DROP TRIGGER IF EXISTS trg_final_reviews_append_only ON final_reviews;
CREATE TRIGGER trg_final_reviews_append_only
BEFORE UPDATE OR DELETE ON final_reviews
FOR EACH ROW EXECUTE FUNCTION reject_historical_output_mutation();

DROP TRIGGER IF EXISTS trg_audit_trail_entries_append_only ON audit_trail_entries;
CREATE TRIGGER trg_audit_trail_entries_append_only
BEFORE UPDATE OR DELETE ON audit_trail_entries
FOR EACH ROW EXECUTE FUNCTION reject_historical_output_mutation();
