-- Personal research records are version-pinned evidence, not mutable state.
-- Draft Books remain editable until locked, but their ownership/version never
-- changes. Saved DCFs, memo versions, and exported audit packs are append-only.

CREATE TABLE IF NOT EXISTS legacy_account_identities (
    legacy_user_id VARCHAR(320) PRIMARY KEY,
    account_user_id VARCHAR(80) NOT NULL
        REFERENCES user_accounts(user_id) ON DELETE RESTRICT,
    legacy_email VARCHAR(320) NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (legacy_user_id, account_user_id)
);

CREATE INDEX IF NOT EXISTS ix_legacy_account_identities_account
    ON legacy_account_identities (account_user_id);

CREATE OR REPLACE FUNCTION personal_record_owner_is_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.user_id IS DISTINCT FROM NEW.user_id
       OR OLD.owner_state IS DISTINCT FROM NEW.owner_state
       OR OLD.universe_version IS DISTINCT FROM NEW.universe_version THEN
        -- The only supported legacy repair is driven by a durable identity
        -- captured from the original JSON account. Email coincidence alone
        -- is never enough to claim a quarantined record.
        IF NOT (
            OLD.owner_state = 'quarantined'
            AND NEW.owner_state = 'owned'
            AND OLD.universe_version IS NOT DISTINCT FROM NEW.universe_version
            AND EXISTS (
                SELECT 1
                  FROM legacy_account_identities AS identity
                 WHERE identity.legacy_user_id = OLD.user_id
                   AND identity.account_user_id = NEW.user_id
            )
        ) THEN
            RAISE EXCEPTION
                '% ownership and universe version are immutable after creation',
                TG_TABLE_NAME;
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION guard_saved_book_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.locked_at IS NOT NULL THEN
            RAISE EXCEPTION 'locked Books cannot be deleted';
        END IF;
        IF EXISTS (SELECT 1 FROM audit_exports WHERE book_id = OLD.book_id) THEN
            RAISE EXCEPTION
                'Books with immutable audit exports cannot be deleted';
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.user_id IS DISTINCT FROM NEW.user_id
       OR OLD.owner_state IS DISTINCT FROM NEW.owner_state
       OR OLD.universe_version IS DISTINCT FROM NEW.universe_version THEN
        IF NOT (
            OLD.owner_state = 'quarantined'
            AND NEW.owner_state = 'owned'
            AND OLD.universe_version IS NOT DISTINCT FROM NEW.universe_version
            AND EXISTS (
                SELECT 1
                  FROM legacy_account_identities AS identity
                 WHERE identity.legacy_user_id = OLD.user_id
                   AND identity.account_user_id = NEW.user_id
            )
        ) THEN
            RAISE EXCEPTION
                'saved_books ownership and universe version are immutable after creation';
        END IF;
    END IF;

    IF OLD.locked_at IS NOT NULL
       AND NEW.locked_at IS NOT NULL
       AND (
           NEW.name IS DISTINCT FROM OLD.name
           OR NEW.recipe_id IS DISTINCT FROM OLD.recipe_id
           OR NEW.constraints IS DISTINCT FROM OLD.constraints
           OR NEW.locked_at IS DISTINCT FROM OLD.locked_at
           OR NEW.lock_acknowledgements IS DISTINCT FROM OLD.lock_acknowledgements
           OR NEW.lock_version IS DISTINCT FROM OLD.lock_version
           OR NEW.lock_payload IS DISTINCT FROM OLD.lock_payload
       ) THEN
        RAISE EXCEPTION
            'locked Book content is immutable; unlock before editing';
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION guard_locked_book_holdings()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    locked_time TIMESTAMPTZ;
BEGIN
    SELECT locked_at INTO locked_time
      FROM saved_books
     WHERE book_id = COALESCE(NEW.book_id, OLD.book_id);

    IF locked_time IS NOT NULL THEN
        RAISE EXCEPTION 'holdings for a locked Book are immutable';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION reject_personal_history_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- One-time reconciliation of a quarantined legacy row is safe only when
    -- its original identity was imported from the old account store. Preserve
    -- every research payload byte while allowing that ownership repair.
    IF TG_OP = 'UPDATE'
       AND OLD.owner_state = 'quarantined'
       AND NEW.owner_state = 'owned'
       AND OLD.universe_version IS NOT DISTINCT FROM NEW.universe_version
       AND EXISTS (
           SELECT 1
             FROM legacy_account_identities AS identity
            WHERE identity.legacy_user_id = OLD.user_id
              AND identity.account_user_id = NEW.user_id
       )
       AND (
           to_jsonb(NEW) - ARRAY['user_id', 'owner_state', 'visibility']
       ) IS NOT DISTINCT FROM (
           to_jsonb(OLD) - ARRAY['user_id', 'owner_state', 'visibility']
       ) THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION
        '% records are append-only and cannot be % after being recorded',
        TG_TABLE_NAME,
        LOWER(TG_OP);
END $$;

DROP TRIGGER IF EXISTS trg_saved_books_history_integrity ON saved_books;
CREATE TRIGGER trg_saved_books_history_integrity
BEFORE UPDATE OR DELETE ON saved_books
FOR EACH ROW EXECUTE FUNCTION guard_saved_book_history();

DROP TRIGGER IF EXISTS trg_saved_book_holdings_locked_integrity ON saved_book_holdings;
CREATE TRIGGER trg_saved_book_holdings_locked_integrity
BEFORE INSERT OR UPDATE OR DELETE ON saved_book_holdings
FOR EACH ROW EXECUTE FUNCTION guard_locked_book_holdings();

DROP TRIGGER IF EXISTS trg_dcf_runs_owner_immutable ON dcf_runs;
CREATE TRIGGER trg_dcf_runs_owner_immutable
BEFORE UPDATE ON dcf_runs
FOR EACH ROW EXECUTE FUNCTION personal_record_owner_is_immutable();

DROP TRIGGER IF EXISTS trg_company_memos_owner_immutable ON company_memos;
CREATE TRIGGER trg_company_memos_owner_immutable
BEFORE UPDATE ON company_memos
FOR EACH ROW EXECUTE FUNCTION personal_record_owner_is_immutable();

DROP TRIGGER IF EXISTS trg_audit_exports_owner_immutable ON audit_exports;
CREATE TRIGGER trg_audit_exports_owner_immutable
BEFORE UPDATE ON audit_exports
FOR EACH ROW EXECUTE FUNCTION personal_record_owner_is_immutable();

DROP TRIGGER IF EXISTS trg_dcf_runs_append_only ON dcf_runs;
CREATE TRIGGER trg_dcf_runs_append_only
BEFORE UPDATE OR DELETE ON dcf_runs
FOR EACH ROW EXECUTE FUNCTION reject_personal_history_mutation();

DROP TRIGGER IF EXISTS trg_company_memos_append_only ON company_memos;
CREATE TRIGGER trg_company_memos_append_only
BEFORE UPDATE OR DELETE ON company_memos
FOR EACH ROW EXECUTE FUNCTION reject_personal_history_mutation();

DROP TRIGGER IF EXISTS trg_audit_exports_append_only ON audit_exports;
CREATE TRIGGER trg_audit_exports_append_only
BEFORE UPDATE OR DELETE ON audit_exports
FOR EACH ROW EXECUTE FUNCTION reject_personal_history_mutation();
