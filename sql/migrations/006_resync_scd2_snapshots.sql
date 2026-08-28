-- Repair: resynchronise the SCD2 snapshots with the timeline load/scd2.py
-- maintains.
--
-- Why this was needed. The pandas path runs every day at 03:00; dbt ran only
-- when someone typed it. Between 2026-08-25 and 2026-08-28 the legacy opened 39
-- versions on the 26th and 20 on the 27th, and dbt saw none of them: on its next
-- run it compared three days of change at once and collapsed them into 154
-- versions all stamped the 28th.
--
-- Those intermediate transitions cannot be recovered by running dbt again. A
-- customer who changed on the 26th and again on the 28th has two versions in the
-- legacy and one in the snapshot, and no snapshot run can invent the first.
-- public still holds the correct timeline, so it is copied back.
--
-- This is a repair, not a design step, and it stays fixed only because
-- orchestrators/run_pipeline.py now runs dbt build in the same flow. Running the
-- two paths in parallel means nothing unless they run at the same cadence: a
-- reconciliation failure would otherwise be measuring the schedule rather than
-- the models.

BEGIN;

DROP TABLE IF EXISTS analytics.snap_vehicles;
DROP TABLE IF EXISTS analytics.snap_customers;

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
