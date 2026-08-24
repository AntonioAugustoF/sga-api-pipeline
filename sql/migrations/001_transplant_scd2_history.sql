-- Phase 3b of the ELT migration: transplant the SCD2 history the Python path
-- accumulated into the tables dbt snapshots will continue.
--
-- Why this exists: dbt snapshot builds history forward from its first run. The
-- 3,136 historical vehicle versions and 1,684 customer versions exist nowhere
-- else — the API returns current state only — so running dbt snapshot on an
-- empty table would discard them permanently.
--
-- Reversible by design. Nothing here writes to public: on any doubt, drop the
-- two tables in analytics and start again.
--
-- Deliberately NOT idempotent. CREATE TABLE fails if the table already exists,
-- rather than silently discarding versions dbt has added since. Re-running is
-- an explicit decision: drop the table first, and know what you are dropping.

BEGIN;

CREATE TABLE analytics.snap_vehicles AS
SELECT
    codigo_veiculo,
    codigo_situacao,
    valor_fixo,
    codigo_voluntario,
    data_contrato,
    codigo_classificacao,
    codigo_regional,
    codigo_cooperativa,
    valor_fipe_protegido,

    -- Unique because dim_vehicles constrains (codigo_veiculo, valido_de).
    -- dbt only requires uniqueness here; it computes its own ids for the rows
    -- it inserts from now on.
    md5(codigo_veiculo || '|' || valido_de::text) AS dbt_scd_id,

    valido_de::timestamp  AS dbt_updated_at,
    valido_de::timestamp  AS dbt_valid_from,

    -- vigente is not carried over. In the snapshot model "current" is not a
    -- stored fact but a consequence of having no end date, so it is one fewer
    -- column that can drift out of agreement with reality.
    valido_ate::timestamp AS dbt_valid_to
FROM public.dim_vehicles;

CREATE TABLE analytics.snap_customers AS
SELECT
    codigo_associado,
    codigo_situacao,
    codigo_voluntario,
    codigo_classificacao,
    codigo_regional,
    codigo_cooperativa,
    md5(codigo_associado || '|' || valido_de::text) AS dbt_scd_id,
    valido_de::timestamp  AS dbt_updated_at,
    valido_de::timestamp  AS dbt_valid_from,
    valido_ate::timestamp AS dbt_valid_to
FROM public.dim_customers;

ALTER TABLE analytics.snap_vehicles  ADD PRIMARY KEY (dbt_scd_id);
ALTER TABLE analytics.snap_customers ADD PRIMARY KEY (dbt_scd_id);

-- dbt's merge looks up the open version by natural key on every run.
CREATE INDEX ix_snap_vehicles_open  ON analytics.snap_vehicles  (codigo_veiculo)  WHERE dbt_valid_to IS NULL;
CREATE INDEX ix_snap_customers_open ON analytics.snap_customers (codigo_associado) WHERE dbt_valid_to IS NULL;

COMMIT;
