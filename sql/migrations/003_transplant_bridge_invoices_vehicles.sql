-- Phase 4c: seed analytics.bridge_invoices_vehicles with the history the Python
-- path accumulated, for the reason recorded in 002: extraction never returns the
-- full set of invoices, so the model can only ever see the latest batch.
--
-- valor_rateado becomes numeric, matching the model and closing the same debt
-- 002 closed on fact_invoices.
--
-- Reversible: nothing writes to public. Deliberately not idempotent.

BEGIN;

DROP TABLE IF EXISTS analytics.bridge_invoices_vehicles;

CREATE TABLE analytics.bridge_invoices_vehicles AS
SELECT
    b.codigo_boleto,
    b.codigo_veiculo,
    b.qtd_veiculos_boleto,
    b.valor_rateado::numeric  as valor_rateado,
    b.criado_em::timestamptz  as criado_em,
    b.data_referencia
FROM public.bridge_invoices_vehicles b;

ALTER TABLE analytics.bridge_invoices_vehicles
    ADD PRIMARY KEY (codigo_boleto, codigo_veiculo);

CREATE INDEX ix_bridge_veiculo ON analytics.bridge_invoices_vehicles (codigo_veiculo);

COMMIT;
