-- A ranked row is sealed-build content, not a mutable cache. Reuse the
-- lifecycle guard introduced for vectors and gate evaluations so failed or
-- sealed builds cannot receive late ranking output.

DROP TRIGGER IF EXISTS trg_ranked_rows_building_only ON ranked_rows;
CREATE TRIGGER trg_ranked_rows_building_only
BEFORE INSERT OR UPDATE OR DELETE ON ranked_rows
FOR EACH ROW EXECUTE FUNCTION require_building_versioned_content();
