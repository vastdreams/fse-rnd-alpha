-- Bind every claim referenced by an immutable universe to that universe.
-- This is forward-only: historical migration checksums must remain unchanged.

CREATE TABLE IF NOT EXISTS universe_evidence_refs (
    universe_version VARCHAR(80) NOT NULL
        REFERENCES universe_builds(universe_version),
    claim_id VARCHAR(80) NOT NULL
        REFERENCES evidence_claims(claim_id),
    PRIMARY KEY (universe_version, claim_id)
);

CREATE INDEX IF NOT EXISTS ix_universe_evidence_refs_claim
    ON universe_evidence_refs (claim_id);

-- MetricVector claim IDs are nested in JSONB fields. Keep their extraction in
-- one database function so seal-time validation and legacy backfill use the
-- exact same definition.
CREATE OR REPLACE FUNCTION universe_vector_claim_ids(p_vector JSONB)
RETURNS TABLE(claim_id VARCHAR(80))
LANGUAGE sql
IMMUTABLE
AS $$
    WITH RECURSIVE walk(node) AS (
        SELECT p_vector
        UNION ALL
        SELECT child.node
          FROM walk
          CROSS JOIN LATERAL (
              SELECT value AS node
                FROM jsonb_each(
                    CASE
                        WHEN jsonb_typeof(walk.node) = 'object' THEN walk.node
                        ELSE '{}'::jsonb
                    END
                )
              UNION ALL
              SELECT value AS node
                FROM jsonb_array_elements(
                    CASE
                        WHEN jsonb_typeof(walk.node) = 'array' THEN walk.node
                        ELSE '[]'::jsonb
                    END
                )
          ) AS child
    )
    SELECT DISTINCT nested.value::VARCHAR(80)
      FROM walk
      CROSS JOIN LATERAL jsonb_array_elements_text(
          CASE
              WHEN jsonb_typeof(walk.node) = 'object'
               AND jsonb_typeof(walk.node -> 'claim_ids') = 'array'
                  THEN walk.node -> 'claim_ids'
              ELSE '[]'::jsonb
          END
      ) AS nested(value)
     WHERE nested.value <> '';
$$;

CREATE OR REPLACE FUNCTION materialize_universe_evidence_refs(
    p_universe_version VARCHAR(80)
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    inserted_count INTEGER;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM universe_builds WHERE universe_version = p_universe_version
    ) THEN
        RAISE EXCEPTION 'unknown universe build %', p_universe_version;
    END IF;

    IF EXISTS (
        WITH referenced_claims AS (
            SELECT DISTINCT ids.claim_id
              FROM metric_vectors AS vector_row
              CROSS JOIN LATERAL universe_vector_claim_ids(vector_row.vector) AS ids
             WHERE vector_row.universe_version = p_universe_version
        )
        SELECT 1
          FROM referenced_claims
          LEFT JOIN evidence_claims AS claim
            ON claim.claim_id = referenced_claims.claim_id
         WHERE claim.claim_id IS NULL
    ) THEN
        RAISE EXCEPTION
            'universe % references one or more missing evidence claims',
            p_universe_version;
    END IF;

    INSERT INTO universe_evidence_refs (universe_version, claim_id)
    SELECT DISTINCT p_universe_version, ids.claim_id
      FROM metric_vectors AS vector_row
      CROSS JOIN LATERAL universe_vector_claim_ids(vector_row.vector) AS ids
     WHERE vector_row.universe_version = p_universe_version
    ON CONFLICT DO NOTHING;

    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END $$;

-- Preserve available legacy evidence without making an upgrade fail solely
-- because old vectors reference records that were never retained.
INSERT INTO universe_evidence_refs (universe_version, claim_id)
SELECT DISTINCT vector_row.universe_version, ids.claim_id
  FROM metric_vectors AS vector_row
  CROSS JOIN LATERAL universe_vector_claim_ids(vector_row.vector) AS ids
  JOIN evidence_claims AS claim
    ON claim.claim_id = ids.claim_id
ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION reject_sealed_evidence_claim_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    protected_claim VARCHAR(80);
BEGIN
    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;

    protected_claim := OLD.claim_id;
    IF EXISTS (
        SELECT 1
          FROM universe_evidence_refs AS ref
          JOIN universe_builds AS build
            ON build.universe_version = ref.universe_version
         WHERE ref.claim_id = protected_claim
           AND build.status = 'sealed'
    ) THEN
        RAISE EXCEPTION
            'evidence claim % belongs to a sealed universe and cannot be changed',
            protected_claim;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_evidence_claims_immutable ON evidence_claims;
CREATE TRIGGER trg_evidence_claims_immutable
BEFORE UPDATE OR DELETE ON evidence_claims
FOR EACH ROW EXECUTE FUNCTION reject_sealed_evidence_claim_mutation();

CREATE OR REPLACE FUNCTION reject_sealed_source_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    protected_snapshot VARCHAR(80);
BEGIN
    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;

    protected_snapshot := OLD.snapshot_id;
    IF EXISTS (
        SELECT 1
          FROM universe_evidence_refs AS ref
          JOIN universe_builds AS build
            ON build.universe_version = ref.universe_version
          JOIN evidence_claims AS claim
            ON claim.claim_id = ref.claim_id
         WHERE claim.snapshot_id = protected_snapshot
           AND build.status = 'sealed'
    ) THEN
        RAISE EXCEPTION
            'source snapshot % belongs to a sealed universe and cannot be changed',
            protected_snapshot;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_source_snapshots_immutable ON source_snapshots;
CREATE TRIGGER trg_source_snapshots_immutable
BEFORE UPDATE OR DELETE ON source_snapshots
FOR EACH ROW EXECUTE FUNCTION reject_sealed_source_snapshot_mutation();

DROP TRIGGER IF EXISTS trg_universe_evidence_refs_immutable ON universe_evidence_refs;
CREATE TRIGGER trg_universe_evidence_refs_immutable
BEFORE INSERT OR UPDATE OR DELETE ON universe_evidence_refs
FOR EACH ROW EXECUTE FUNCTION reject_sealed_universe_content_mutation();

CREATE OR REPLACE FUNCTION validate_universe_build_evidence_seal()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.status = 'building'
       AND NEW.status = 'sealed'
       AND EXISTS (
           SELECT 1
             FROM metric_vectors AS vector_row
             CROSS JOIN LATERAL universe_vector_claim_ids(vector_row.vector) AS ids
             LEFT JOIN universe_evidence_refs AS ref
               ON ref.universe_version = NEW.universe_version
              AND ref.claim_id = ids.claim_id
            WHERE vector_row.universe_version = NEW.universe_version
              AND ref.claim_id IS NULL
       ) THEN
        RAISE EXCEPTION
            'universe % cannot seal until all vector evidence claims are bound',
            NEW.universe_version;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_validate_universe_build_evidence_seal ON universe_builds;
CREATE TRIGGER trg_validate_universe_build_evidence_seal
BEFORE UPDATE ON universe_builds
FOR EACH ROW EXECUTE FUNCTION validate_universe_build_evidence_seal();
