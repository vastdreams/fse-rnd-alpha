-- Segregate SIMULATED robustness-study snapshots from the clean sealed ledger.
-- kind='sealed'    → real PIT seals (the allocator-facing track record)
-- kind='simulated' → pre-registered proxy-gate study rows; never served as sealed
--
-- The unique key widens to (universe_version, as_of_date, kind) so a simulated
-- study row can coexist with (but never overwrite) a sealed row for the same day.

ALTER TABLE buy_set_snapshots
    ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'sealed';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'buy_set_snapshots_kind_check'
    ) THEN
        ALTER TABLE buy_set_snapshots
            ADD CONSTRAINT buy_set_snapshots_kind_check
            CHECK (kind IN ('sealed', 'simulated'));
    END IF;
END $$;

ALTER TABLE buy_set_snapshots
    DROP CONSTRAINT IF EXISTS buy_set_snapshots_universe_version_as_of_date_key;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'buy_set_snapshots_uv_asof_kind_key'
    ) THEN
        ALTER TABLE buy_set_snapshots
            ADD CONSTRAINT buy_set_snapshots_uv_asof_kind_key
            UNIQUE (universe_version, as_of_date, kind);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_buy_set_snapshots_kind
    ON buy_set_snapshots (kind, universe_version, as_of_date DESC);
