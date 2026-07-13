-- Research vectors and evidence use TIMESTAMP WITHOUT TIME ZONE for historical
-- compatibility. PostgreSQL's CURRENT_TIMESTAMP otherwise adopts the server
-- session timezone while builders write UTC-naive values, making a claim
-- appear to have been extracted after the vector it actually preceded.
--
-- New defaults are explicitly UTC so seal-time point-in-time comparisons are
-- meaningful regardless of the database host timezone. Existing rows are not
-- rewritten: their timezone provenance cannot be reconstructed safely.

ALTER TABLE source_snapshots
    ALTER COLUMN fetched_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE evidence_claims
    ALTER COLUMN extracted_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE metric_vectors
    ALTER COLUMN computed_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE ranked_rows
    ALTER COLUMN computed_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE gate_evaluations
    ALTER COLUMN evaluated_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
