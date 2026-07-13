-- Enforce a one-way, evidence-complete universe lifecycle.
--
-- Earlier releases permitted a direct INSERT of a sealed build because the
-- lifecycle status defaulted to sealed. That bypassed the seal trigger and
-- allowed an empty or unproven build to become active. Existing historical
-- rows remain readable; every new build must now begin as building and pass
-- the same validation path before it can be sealed or activated.

ALTER TABLE universe_builds
    ALTER COLUMN status SET DEFAULT 'building';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_universe_builds_sealed_timestamp'
           AND conrelid = 'universe_builds'::regclass
    ) THEN
        ALTER TABLE universe_builds
            ADD CONSTRAINT ck_universe_builds_sealed_timestamp
            CHECK (status <> 'sealed' OR sealed_at IS NOT NULL) NOT VALID;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION guard_universe_build_lifecycle()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'building'
           OR NEW.is_active
           OR NEW.sealed_at IS NOT NULL THEN
            RAISE EXCEPTION
                'new universe builds must begin as inactive building rows';
        END IF;
        IF NEW.source_sha IS NULL
           OR NEW.source_sha !~ '^[0-9a-f]{40}$' THEN
            RAISE EXCEPTION
                'new universe builds require a full committed source SHA';
        END IF;
        RETURN NEW;
    END IF;

    IF OLD.status = 'building' THEN
        IF NEW.status NOT IN ('building', 'sealed', 'failed') THEN
            RAISE EXCEPTION
                'building universe % has an invalid lifecycle transition to %',
                OLD.universe_version, NEW.status;
        END IF;
        IF NEW.status = 'sealed' AND NEW.sealed_at IS NULL THEN
            RAISE EXCEPTION 'sealed universe % requires sealed_at', NEW.universe_version;
        END IF;
        IF NEW.status = 'sealed'
           AND (NEW.source_sha IS NULL OR NEW.source_sha !~ '^[0-9a-f]{40}$') THEN
            RAISE EXCEPTION 'sealed universe % requires a committed source SHA', NEW.universe_version;
        END IF;
    ELSIF OLD.status = 'sealed' THEN
        IF NEW.universe_version IS DISTINCT FROM OLD.universe_version
           OR NEW.input_sha256 IS DISTINCT FROM OLD.input_sha256
           OR NEW.manifest IS DISTINCT FROM OLD.manifest
           OR NEW.parent_version IS DISTINCT FROM OLD.parent_version
           OR NEW.engine_version IS DISTINCT FROM OLD.engine_version
           OR NEW.created_at IS DISTINCT FROM OLD.created_at
           OR NEW.sealed_at IS DISTINCT FROM OLD.sealed_at
           OR NEW.status IS DISTINCT FROM OLD.status
           OR NEW.source_sha IS DISTINCT FROM OLD.source_sha
           OR (
                NEW.data_manifest_sha256 IS DISTINCT FROM OLD.data_manifest_sha256
                AND NOT (
                    OLD.data_manifest_sha256 IS NULL
                    AND NEW.data_manifest_sha256 IS NOT NULL
                )
           ) THEN
            RAISE EXCEPTION 'sealed universe build % is immutable', OLD.universe_version;
        END IF;
    ELSE
        IF NEW.status IS DISTINCT FROM OLD.status
           OR NEW.is_active THEN
            RAISE EXCEPTION
                'failed or superseded universe % cannot be reactivated',
                OLD.universe_version;
        END IF;
    END IF;

    IF NEW.is_active THEN
        IF NEW.status <> 'sealed'
           OR NEW.data_manifest_sha256 IS NULL
           OR NEW.data_manifest_sha256 !~ '^[0-9a-f]{64}$' THEN
            RAISE EXCEPTION
                'only a sealed build bound to an immutable data manifest may be active';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION validate_universe_build_evidence_seal()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.status = 'building'
       AND NEW.status = 'sealed' THEN
        IF NOT EXISTS (
            SELECT 1
              FROM metric_vectors
             WHERE universe_version = NEW.universe_version
        ) THEN
            RAISE EXCEPTION
                'universe % cannot seal without at least one metric vector',
                NEW.universe_version;
        END IF;

        IF EXISTS (
            SELECT 1
              FROM metric_vectors AS vector_row
              CROSS JOIN LATERAL universe_vector_claim_ids(vector_row.vector) AS ids
              LEFT JOIN universe_evidence_refs AS ref
                ON ref.universe_version = NEW.universe_version
               AND ref.claim_id = ids.claim_id
              LEFT JOIN evidence_claims AS claim
                ON claim.claim_id = ids.claim_id
              LEFT JOIN source_snapshots AS snapshot
                ON snapshot.snapshot_id = claim.snapshot_id
             WHERE vector_row.universe_version = NEW.universe_version
               AND (
                    ref.claim_id IS NULL
                    OR claim.claim_id IS NULL
                    OR snapshot.snapshot_id IS NULL
                    OR claim.ticker IS DISTINCT FROM vector_row.ticker
                    OR snapshot.ticker IS DISTINCT FROM claim.ticker
                    OR claim.extracted_at > vector_row.computed_at
                    OR snapshot.available_date > vector_row.computed_at::date
               )
        ) THEN
            RAISE EXCEPTION
                'universe % cannot seal until vector evidence is bound, ticker-consistent, and point-in-time valid',
                NEW.universe_version;
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION require_building_versioned_content()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    content_version VARCHAR(80);
BEGIN
    content_version := COALESCE(NEW.universe_version, OLD.universe_version);
    IF content_version IS NULL THEN
        RAISE EXCEPTION '% requires a universe version', TG_TABLE_NAME;
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM universe_builds
         WHERE universe_version = content_version
           AND status = 'building'
    ) THEN
        RAISE EXCEPTION
            '% can only be written while its universe build is building',
            TG_TABLE_NAME;
    END IF;
    IF TG_OP = 'UPDATE'
       AND NEW.universe_version IS DISTINCT FROM OLD.universe_version THEN
        RAISE EXCEPTION '% cannot be moved between universe versions', TG_TABLE_NAME;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_metric_vectors_building_only ON metric_vectors;
CREATE TRIGGER trg_metric_vectors_building_only
BEFORE INSERT OR UPDATE OR DELETE ON metric_vectors
FOR EACH ROW EXECUTE FUNCTION require_building_versioned_content();

DROP TRIGGER IF EXISTS trg_gate_evaluations_building_only ON gate_evaluations;
CREATE TRIGGER trg_gate_evaluations_building_only
BEFORE INSERT OR UPDATE OR DELETE ON gate_evaluations
FOR EACH ROW EXECUTE FUNCTION require_building_versioned_content();
