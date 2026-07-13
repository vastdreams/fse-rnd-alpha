-- Migration: 009_immutable_audit_export_payload.sql
-- Purpose: retain the exact server-generated Book audit payload behind each
--          export hash, so an unlock/edit cannot rewrite historical evidence.

ALTER TABLE audit_exports
    ADD COLUMN IF NOT EXISTS payload JSONB;
