-- 009_reduce_delinquency_to_last_batch_of_day.sql
--
-- Finishes what 008 was meant to do and did not. Step 3 of that migration
-- anchored the delete to max(dt_referencia); by the time it ran, the batch of
-- 2026-08-29 had already landed, so it repaired a date where the two paths
-- already agreed and left 2026-08-28 untouched.
--
-- The divergence itself is described in 008: two extractions on 2026-08-28
-- (03:06 and 16:24). load_delinquency_snapshot.py deletes dt_referencia and
-- reinserts it, so public holds the last observation of the day. The dbt model
-- merges and never deletes, so analytics holds the union -- 58 boletos that
-- were open in the morning and settled by the afternoon.
--
-- A daily snapshot means the state on dt_referencia, and the last observation
-- of the day is that state. This anchors on the date rather than on "the most
-- recent one", and repairs every date at once.
--
-- Deletion is confined to dates that raw still covers (from 2026-08-18). The
-- fact reaches back to 2026-07-01 through the transplant in migration 004;
-- those dates have no batch to be judged against and are left alone.

BEGIN;

CREATE TEMP TABLE authoritative_delinquency ON COMMIT DROP AS
WITH last_batch_of_day AS (
    SELECT max(_extracted_at) AS _extracted_at
    FROM raw.delinquency
    GROUP BY (_extracted_at AT TIME ZONE 'America/Sao_Paulo')::date
)
SELECT
    (r._extracted_at AT TIME ZONE 'America/Sao_Paulo')::date AS dt_referencia,

    -- Mirrors the clean_json_string macro, U+00A0 included. Comparing the raw
    -- payload against a cleaned column would silently spare rows that differ
    -- only by an invisible character.
    lower(btrim(r.payload ->> 'codigo_boleto', E' \t\n\r\f\v' || U&'\00A0')) AS codigo_boleto
FROM raw.delinquency r
JOIN last_batch_of_day b USING (_extracted_at);

CREATE INDEX ON authoritative_delinquency (dt_referencia, codigo_boleto);

DELETE FROM analytics.fact_delinquency_snapshot f
WHERE f.dt_referencia IN (SELECT DISTINCT dt_referencia FROM authoritative_delinquency)
  AND NOT EXISTS (
      SELECT 1
      FROM authoritative_delinquency a
      WHERE a.dt_referencia = f.dt_referencia
        AND a.codigo_boleto = f.codigo_boleto
  );

-- Assert that both paths now agree, date by date, over the range raw covers.
DO $$
DECLARE
    disagreeing integer;
BEGIN
    SELECT count(*) INTO disagreeing
    FROM (
        SELECT dt_referencia, count(*) AS n
        FROM analytics.fact_delinquency_snapshot
        WHERE dt_referencia IN (SELECT DISTINCT dt_referencia FROM authoritative_delinquency)
        GROUP BY dt_referencia
    ) a
    FULL JOIN (
        SELECT dt_referencia, count(*) AS n
        FROM public.fact_delinquency_snapshot
        WHERE dt_referencia IN (SELECT DISTINCT dt_referencia FROM authoritative_delinquency)
        GROUP BY dt_referencia
    ) l USING (dt_referencia)
    WHERE a.n IS DISTINCT FROM l.n;

    IF disagreeing > 0 THEN
        RAISE EXCEPTION '% date(s) still differ between analytics and public', disagreeing;
    END IF;
END $$;

COMMIT;
