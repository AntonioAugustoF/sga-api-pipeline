-- fact_invoices becomes a view over fact_invoices_base.
--
-- dias_em_atraso and faixa_atraso were persisted by an incremental merge, so an
-- invoice kept the age it had the last night it fell inside an extraction
-- window: 5,027 unpaid invoices were in the wrong band on 2026-11-27. They are
-- a function of the day the fact is read, and dbt now computes them in the
-- fact_invoices view.
--
-- The table keeps its 300k+ rows of accumulated history, which raw cannot
-- rebuild: it is renamed, never recreated. Run once, before the first dbt build
-- that contains models/marts/fact_invoices_base.sql; the build then creates the
-- fact_invoices view on top of it.
--
-- Idempotent: each step checks the state it expects.

BEGIN;

DO $$
BEGIN
    IF to_regclass('analytics.fact_invoices_base') IS NULL
       AND EXISTS (
           SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'analytics' AND c.relname = 'fact_invoices' AND c.relkind = 'r'
       )
    THEN
        ALTER TABLE analytics.fact_invoices RENAME TO fact_invoices_base;
        ALTER INDEX IF EXISTS analytics.fact_invoices_pkey RENAME TO fact_invoices_base_pkey;
        ALTER INDEX IF EXISTS analytics.ix_fact_invoices_emissao RENAME TO ix_fact_invoices_base_emissao;
    END IF;
END $$;

ALTER TABLE analytics.fact_invoices_base DROP COLUMN IF EXISTS dias_em_atraso;
ALTER TABLE analytics.fact_invoices_base DROP COLUMN IF EXISTS faixa_atraso;

COMMIT;
