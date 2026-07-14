-- PIT research-BUY membership ledger (distinct from paper HML_RD).
-- Append-only via application seal; do not invent historical rows.

CREATE TABLE IF NOT EXISTS buy_set_snapshots (
    snapshot_id        TEXT PRIMARY KEY,
    universe_version   TEXT NOT NULL,
    as_of_date         DATE NOT NULL,
    sealed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    engine_version     TEXT NOT NULL,
    source_sha         TEXT,
    n_buy              INTEGER NOT NULL CHECK (n_buy >= 0),
    note               TEXT,
    UNIQUE (universe_version, as_of_date)
);

CREATE TABLE IF NOT EXISTS buy_set_members (
    snapshot_id        TEXT NOT NULL REFERENCES buy_set_snapshots(snapshot_id) ON DELETE CASCADE,
    ticker             TEXT NOT NULL,
    stance             TEXT NOT NULL CHECK (stance = 'BUY'),
    confidence         TEXT,
    score              DOUBLE PRECISION,
    mos_live           DOUBLE PRECISION,
    gap_to_median      DOUBLE PRECISION,
    horizon_years      INTEGER,
    implied_ann_return DOUBLE PRECISION,
    PRIMARY KEY (snapshot_id, ticker)
);

CREATE INDEX IF NOT EXISTS ix_buy_set_snapshots_uv
    ON buy_set_snapshots (universe_version, as_of_date DESC);
