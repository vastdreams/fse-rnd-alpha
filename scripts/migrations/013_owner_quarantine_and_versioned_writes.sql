-- Quarantine legacy personal records whose owner/version cannot be proved, and
-- make every future personal write carry a durable account and sealed universe.

ALTER TABLE saved_books
    ADD COLUMN IF NOT EXISTS owner_state VARCHAR(16) NOT NULL DEFAULT 'owned';
ALTER TABLE dcf_runs
    ADD COLUMN IF NOT EXISTS owner_state VARCHAR(16) NOT NULL DEFAULT 'owned';
ALTER TABLE company_memos
    ADD COLUMN IF NOT EXISTS owner_state VARCHAR(16) NOT NULL DEFAULT 'owned';
ALTER TABLE audit_exports
    ADD COLUMN IF NOT EXISTS owner_state VARCHAR(16) NOT NULL DEFAULT 'owned';

DO $$
DECLARE
    table_name TEXT;
    constraint_name TEXT;
BEGIN
    FOR table_name, constraint_name IN
        SELECT * FROM (VALUES
            ('saved_books', 'ck_saved_books_owner_state'),
            ('dcf_runs', 'ck_dcf_runs_owner_state'),
            ('company_memos', 'ck_company_memos_owner_state'),
            ('audit_exports', 'ck_audit_exports_owner_state')
        ) AS constraints(table_name, constraint_name)
    LOOP
        IF NOT EXISTS (
            SELECT 1
              FROM pg_constraint
             WHERE conname = constraint_name
               AND conrelid = table_name::regclass
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I ADD CONSTRAINT %I CHECK (owner_state IN (''owned'', ''quarantined''))',
                table_name,
                constraint_name
            );
        END IF;
    END LOOP;
END $$;

-- A legacy row is visible only after its account and immutable research
-- version can be proven. The routes below also filter owner_state, so an old
-- email-shaped owner ID or NULL can never be claimed by a later registrant.
UPDATE saved_books AS record
   SET owner_state = 'quarantined'
 WHERE record.user_id IS NULL
    OR record.universe_version IS NULL
    OR NOT EXISTS (
        SELECT 1 FROM user_accounts AS account
         WHERE account.user_id = record.user_id
    )
    OR NOT EXISTS (
        SELECT 1 FROM universe_builds AS build
         WHERE build.universe_version = record.universe_version
           AND build.status = 'sealed'
    );

-- The partial unique primary-book index is per user ID rather than ownership
-- state. A hidden legacy primary must not prevent that user from creating a
-- visible primary Book after registration.
UPDATE saved_books
   SET is_primary = false
 WHERE owner_state = 'quarantined'
   AND is_primary;

UPDATE company_memos AS record
   SET owner_state = 'quarantined'
 WHERE record.user_id IS NULL
    OR record.universe_version IS NULL
    OR NOT EXISTS (
        SELECT 1 FROM user_accounts AS account
         WHERE account.user_id = record.user_id
    )
    OR NOT EXISTS (
        SELECT 1 FROM universe_builds AS build
         WHERE build.universe_version = record.universe_version
           AND build.status = 'sealed'
    );

UPDATE audit_exports AS record
   SET owner_state = 'quarantined'
 WHERE record.user_id IS NULL
    OR record.universe_version IS NULL
    OR NOT EXISTS (
        SELECT 1 FROM user_accounts AS account
         WHERE account.user_id = record.user_id
    )
    OR NOT EXISTS (
        SELECT 1 FROM universe_builds AS build
         WHERE build.universe_version = record.universe_version
           AND build.status = 'sealed'
    );

-- Replace the earlier private/reference check before introducing the explicit
-- quarantine state. Legacy NULL-owner DCFs must never become shared records.
ALTER TABLE dcf_runs
    DROP CONSTRAINT IF EXISTS ck_dcf_runs_visibility_owner;

UPDATE dcf_runs AS record
   SET owner_state = 'quarantined',
       visibility = 'quarantined'
 WHERE record.user_id IS NULL
    OR record.universe_version IS NULL
    OR NOT EXISTS (
        SELECT 1 FROM user_accounts AS account
         WHERE account.user_id = record.user_id
    )
    OR NOT EXISTS (
        SELECT 1 FROM universe_builds AS build
         WHERE build.universe_version = record.universe_version
           AND build.status = 'sealed'
    );

ALTER TABLE dcf_runs
    ADD CONSTRAINT ck_dcf_runs_visibility_owner
    CHECK (
        (visibility = 'private' AND owner_state = 'owned' AND user_id IS NOT NULL)
        OR
        (visibility = 'reference' AND owner_state = 'owned' AND user_id IS NULL)
        OR
        (visibility = 'quarantined' AND owner_state = 'quarantined')
    ) NOT VALID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_saved_books_universe'
           AND conrelid = 'saved_books'::regclass
    ) THEN
        ALTER TABLE saved_books
            ADD CONSTRAINT fk_saved_books_universe
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_dcf_runs_universe'
           AND conrelid = 'dcf_runs'::regclass
    ) THEN
        ALTER TABLE dcf_runs
            ADD CONSTRAINT fk_dcf_runs_universe
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_company_memos_universe'
           AND conrelid = 'company_memos'::regclass
    ) THEN
        ALTER TABLE company_memos
            ADD CONSTRAINT fk_company_memos_universe
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_audit_exports_universe'
           AND conrelid = 'audit_exports'::regclass
    ) THEN
        ALTER TABLE audit_exports
            ADD CONSTRAINT fk_audit_exports_universe
            FOREIGN KEY (universe_version)
            REFERENCES universe_builds(universe_version) NOT VALID;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION require_owned_sealed_research_record()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.owner_state <> 'owned'
       OR NEW.user_id IS NULL
       OR NEW.universe_version IS NULL THEN
        RAISE EXCEPTION
            '% requires an owned durable user and sealed universe version',
            TG_TABLE_NAME;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM user_accounts WHERE user_id = NEW.user_id
    ) THEN
        RAISE EXCEPTION '% has no durable account owner', TG_TABLE_NAME;
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM universe_builds
         WHERE universe_version = NEW.universe_version
           AND status = 'sealed'
    ) THEN
        RAISE EXCEPTION '% requires a sealed universe version', TG_TABLE_NAME;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_saved_books_owned_versioned ON saved_books;
CREATE TRIGGER trg_saved_books_owned_versioned
BEFORE INSERT OR UPDATE ON saved_books
FOR EACH ROW EXECUTE FUNCTION require_owned_sealed_research_record();

DROP TRIGGER IF EXISTS trg_company_memos_owned_versioned ON company_memos;
CREATE TRIGGER trg_company_memos_owned_versioned
BEFORE INSERT OR UPDATE ON company_memos
FOR EACH ROW EXECUTE FUNCTION require_owned_sealed_research_record();

DROP TRIGGER IF EXISTS trg_audit_exports_owned_versioned ON audit_exports;
CREATE TRIGGER trg_audit_exports_owned_versioned
BEFORE INSERT OR UPDATE ON audit_exports
FOR EACH ROW EXECUTE FUNCTION require_owned_sealed_research_record();

CREATE OR REPLACE FUNCTION require_dcf_owner_scope()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.owner_state = 'quarantined' THEN
        RAISE EXCEPTION 'quarantined DCF records are legacy-only and cannot be written';
    END IF;
    IF NEW.universe_version IS NULL OR NOT EXISTS (
        SELECT 1
          FROM universe_builds
         WHERE universe_version = NEW.universe_version
           AND status = 'sealed'
    ) THEN
        RAISE EXCEPTION 'DCF records require a sealed universe version';
    END IF;
    IF NEW.visibility = 'private' THEN
        IF NEW.user_id IS NULL OR NOT EXISTS (
            SELECT 1 FROM user_accounts WHERE user_id = NEW.user_id
        ) THEN
            RAISE EXCEPTION 'private DCF records require a durable account owner';
        END IF;
    ELSIF NEW.visibility = 'reference' THEN
        IF NEW.user_id IS NOT NULL THEN
            RAISE EXCEPTION 'reference DCF records must not have a personal owner';
        END IF;
    ELSE
        RAISE EXCEPTION 'unsupported DCF visibility %', NEW.visibility;
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_dcf_runs_owner_scope ON dcf_runs;
CREATE TRIGGER trg_dcf_runs_owner_scope
BEFORE INSERT OR UPDATE ON dcf_runs
FOR EACH ROW EXECUTE FUNCTION require_dcf_owner_scope();
