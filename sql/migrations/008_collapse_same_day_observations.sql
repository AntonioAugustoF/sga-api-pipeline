-- 008_collapse_same_day_observations.sql
--
-- Repairs what two extractions on one day left behind. On 2026-08-28 the
-- nightly flow ran at 03:02 on the pre-dbt code, and the rebuilt flow was run
-- by hand at 16:11. Both paths saw both batches; they disagree on what a
-- second observation in the same day means.
--
--   SCD2 -- public.dim_* store valido_de as DATE, so a second change on the
--   same day overwrites the first and no version is created. The dbt snapshot
--   has timestamp grain: it closed the morning versions at 16:25:30 and opened
--   successors, leaving 25 versions that open and close on the same date.
--   Those are not representable at the grain the marts expose, and they make
--   the point-in-time joins that resolve sk_customer and sk_vehicle ambiguous
--   -- two versions valid on one date. They are collapsed into their
--   successors, which keeps the chain continuous and loses nothing the marts
--   could have shown.
--
--   Delinquency -- load_delinquency_snapshot.py deletes dt_referencia and
--   reinserts it; the dbt model merges and never deletes. 58 boletos present
--   at 03:02 and gone by 16:11 survived only on the dbt side. A daily snapshot
--   means the state on dt_referencia, and the last observation of the day is
--   that state.
--
-- From 2026-08-28 the flow extracts and builds dbt once per night, so this
-- divergence does not recur on its own. It recurs if the flow is run twice in
-- one day, which is why this is written to repair any same-day pair rather
-- than today's specific rows.

BEGIN;

-- Guard: this collapses one version into its immediate successor. Chained
-- zero-length versions would need to be collapsed repeatedly, and silently
-- doing half the job is exactly the failure mode this project rejects.
DO $$
DECLARE
    chained integer;
BEGIN
    SELECT count(*) INTO chained
    FROM analytics.snap_customers a
    JOIN analytics.snap_customers b
      ON b.codigo_associado = a.codigo_associado
     AND b.dbt_valid_from   = a.dbt_valid_to
    WHERE a.dbt_valid_to IS NOT NULL
      AND a.dbt_valid_from::date = a.dbt_valid_to::date
      AND b.dbt_valid_to IS NOT NULL
      AND b.dbt_valid_from::date = b.dbt_valid_to::date;

    IF chained > 0 THEN
        RAISE EXCEPTION 'snap_customers has % chained zero-length versions; collapse is not single-pass', chained;
    END IF;

    SELECT count(*) INTO chained
    FROM analytics.snap_vehicles a
    JOIN analytics.snap_vehicles b
      ON b.codigo_veiculo = a.codigo_veiculo
     AND b.dbt_valid_from = a.dbt_valid_to
    WHERE a.dbt_valid_to IS NOT NULL
      AND a.dbt_valid_from::date = a.dbt_valid_to::date
      AND b.dbt_valid_to IS NOT NULL
      AND b.dbt_valid_from::date = b.dbt_valid_to::date;

    IF chained > 0 THEN
        RAISE EXCEPTION 'snap_vehicles has % chained zero-length versions; collapse is not single-pass', chained;
    END IF;
END $$;


-- 1. Collapse zero-length customer versions ---------------------------------

CREATE TEMP TABLE collapse_customers ON COMMIT DROP AS
SELECT dbt_scd_id, codigo_associado, dbt_valid_from, dbt_valid_to
FROM analytics.snap_customers
WHERE dbt_valid_to IS NOT NULL
  AND dbt_valid_from::date = dbt_valid_to::date;

-- The successor inherits the start date. dbt_scd_id is deliberately left
-- alone: dbt only requires it to be unique, and rewriting a primary key it
-- may hold a reference to buys nothing.
UPDATE analytics.snap_customers s
SET dbt_valid_from = c.dbt_valid_from,
    dbt_updated_at = c.dbt_valid_from
FROM collapse_customers c
WHERE s.codigo_associado = c.codigo_associado
  AND s.dbt_valid_from   = c.dbt_valid_to;

DELETE FROM analytics.snap_customers s
USING collapse_customers c
WHERE s.dbt_scd_id = c.dbt_scd_id;


-- 2. Collapse zero-length vehicle versions ----------------------------------

CREATE TEMP TABLE collapse_vehicles ON COMMIT DROP AS
SELECT dbt_scd_id, codigo_veiculo, dbt_valid_from, dbt_valid_to
FROM analytics.snap_vehicles
WHERE dbt_valid_to IS NOT NULL
  AND dbt_valid_from::date = dbt_valid_to::date;

UPDATE analytics.snap_vehicles s
SET dbt_valid_from = c.dbt_valid_from,
    dbt_updated_at = c.dbt_valid_from
FROM collapse_vehicles c
WHERE s.codigo_veiculo = c.codigo_veiculo
  AND s.dbt_valid_from = c.dbt_valid_to;

DELETE FROM analytics.snap_vehicles s
USING collapse_vehicles c
WHERE s.dbt_scd_id = c.dbt_scd_id;


-- 3. Reduce the latest delinquency date to the last observation of the day ---

DELETE FROM analytics.fact_delinquency_snapshot f
WHERE f.dt_referencia = (SELECT max(dt_referencia) FROM analytics.fact_delinquency_snapshot)
  AND NOT EXISTS (
      SELECT 1
      FROM analytics.stg_sga__delinquency s
      WHERE s.codigo_boleto = f.codigo_boleto
  );


-- 4. Assert the repair ------------------------------------------------------

DO $$
DECLARE
    leftover integer;
BEGIN
    SELECT count(*) INTO leftover
    FROM (
        SELECT 1 FROM analytics.snap_customers
        WHERE dbt_valid_to IS NOT NULL AND dbt_valid_from::date = dbt_valid_to::date
        UNION ALL
        SELECT 1 FROM analytics.snap_vehicles
        WHERE dbt_valid_to IS NOT NULL AND dbt_valid_from::date = dbt_valid_to::date
    ) x;

    IF leftover > 0 THEN
        RAISE EXCEPTION '% zero-length versions remain after collapse', leftover;
    END IF;
END $$;

COMMIT;
