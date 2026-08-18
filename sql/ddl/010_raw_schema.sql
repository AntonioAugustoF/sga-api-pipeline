-- Raw landing layer for the ELT migration.
--
-- Invariants that must hold for every table in this schema:
--   * Append-only. No UPDATE, no DELETE. Reprocessing reads history; it does
--     not rewrite it. This is what makes a past day reproducible without
--     recalling the API, and it is property that actually defines ELT.
--   * payload is the API response untouched. Flattening is the transformation and
--     belongs to dbt.
--   * _extracted_at is identical for every row of one extraction batch, so a
--     staging model can isolate a batch with a single max() filter instead of
--     a date range that could straddle two runs.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.regionals (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.cooperatives (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.statuses (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.volunteers (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.customers (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.vehicles (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.invoices (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.invoice_statuses (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.delinquency (
    _extracted_at timestamptz NOT NULL,
    _endpoint     text        NOT NULL,
    payload       jsonb       NOT NULL
);


CREATE INDEX IF NOT EXISTS ix_raw_regionals_extracted_at        ON raw.regionals         (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_cooperatives_extracted_at     ON raw.cooperatives      (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_statuses_extracted_at         ON raw.statuses          (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_volunteers_extracted_at       ON raw.volunteers        (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_customers_extracted_at        ON raw.customers         (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_vehicles_extracted_at         ON raw.vehicles          (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_invoices_extracted_at         ON raw.invoices          (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_invoice_statuses_extracted_at ON raw.invoice_statuses  (_extracted_at DESC);
CREATE INDEX IF NOT EXISTS ix_raw_delinquency_extracted_at      ON raw.delinquency       (_extracted_at DESC);