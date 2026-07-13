-- Quarantined legacy records remain retained for audit purposes, but every
-- future personal record must reference a durable public account at the
-- database boundary as well as in the API route.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_saved_books_owner_account'
           AND conrelid = 'saved_books'::regclass
    ) THEN
        ALTER TABLE saved_books
            ADD CONSTRAINT fk_saved_books_owner_account
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_dcf_runs_owner_account'
           AND conrelid = 'dcf_runs'::regclass
    ) THEN
        ALTER TABLE dcf_runs
            ADD CONSTRAINT fk_dcf_runs_owner_account
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_company_memos_owner_account'
           AND conrelid = 'company_memos'::regclass
    ) THEN
        ALTER TABLE company_memos
            ADD CONSTRAINT fk_company_memos_owner_account
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'fk_audit_exports_owner_account'
           AND conrelid = 'audit_exports'::regclass
    ) THEN
        ALTER TABLE audit_exports
            ADD CONSTRAINT fk_audit_exports_owner_account
            FOREIGN KEY (user_id) REFERENCES user_accounts(user_id) NOT VALID;
    END IF;
END $$;
