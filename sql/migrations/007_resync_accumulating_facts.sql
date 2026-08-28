-- Repair: resynchronise the two accumulating facts with the tables the pandas
-- path writes, for the same reason as 006.
--
-- dbt last ran on 2026-08-25 and next on the 28th. In between the pandas path
-- ran twice, and the two facts drifted in different ways:
--
--   fact_delinquency_snapshot lost two whole days. Its grain is one row per
--   invoice per reference date, so 2026-08-26 (6,469 rows) and 2026-08-27
--   (7,588 rows) simply do not exist on the dbt side. A daily photograph cannot
--   be taken retroactively.
--
--   fact_invoices lost no rows, but 194 carry a stale dias_em_atraso. The
--   measure is recomputed against the current date for whatever is in the batch;
--   the legacy recomputed on the 26th and 27th and dbt did not.
--
-- Neither is recoverable by running dbt again, so public is copied back.
--
-- This stays fixed only because orchestrators/run_pipeline.py now builds dbt in
-- the same flow. A daily fact reconciled against a warehouse built three days
-- ago is measuring the schedule, not the models.

BEGIN;

-- CASCADE because the delinquency views select from this fact. dbt recreates
-- them on the next build; they hold no state of their own.
DROP TABLE IF EXISTS analytics.fact_invoices CASCADE;
DROP TABLE IF EXISTS analytics.fact_delinquency_snapshot CASCADE;

CREATE TABLE analytics.fact_invoices AS
SELECT
    f.codigo_associado,
    f.nome_associado,
    f.cpf_associado,
    f.codigo_situacao_associado,
    f.descricao_situacao_associado,
    f.codigo_regional_associado,
    f.nome_regional_associado,
    f.codigo_boleto,
    f.nosso_numero,
    f.codigo_situacao_boleto,
    f.descricao_situacao_boleto,
    f.pago,
    f.codigo_regional,
    f.nome_regional_boleto,
    f.mes_referente,
    f.data_emissao,
    f.data_vencimento_original,
    f.data_vencimento,
    f.valor_boleto::numeric as valor_boleto,
    f.data_pagamento,
    f.valor_pagamento::numeric as valor_pagamento,
    f.data_credito_banco,
    f.referente,
    f.codigo_mgfformapagamento,
    f.codigo_forma_pagamento,
    f.descricao_forma_pagamento,
    f.tarifa_cobranca_banco::numeric as tarifa_cobranca_banco,
    f.parcela_paga,
    f.qtde_parcela,
    f.descricao_tipo_cobranca_recorrente,
    f.codigo_tipo_boleto,
    f.descricao_tipo_boleto,
    f.codigo_conta,
    f.codigo_banco,
    f.nome_banco,
    f.agencia,
    f.conta,
    f.descricao_tipo_baixa_boleto,
    f.veiculo,
    f.beneficiario,
    f.codigo_situacao,
    f.dias_em_atraso::integer as dias_em_atraso,
    f.faixa_atraso,
    f.status_pagamento,
    f.diferenca_pagamento::numeric as diferenca_pagamento,

    -- The legacy integer resolved to its version, then forward to the hash.
    nova.sk_customer,

    -- timestamptz to match dbt.current_timestamp() in the model. The legacy
    -- column is naive; these values were written by the pipeline running
    -- locally, so the session zone is the right interpretation.
    f.criado_em::timestamptz as criado_em,
    f.data_referencia,
    f.controle_carne,
    f.parcelado
FROM public.fact_invoices f
LEFT JOIN public.dim_customers antiga
       ON antiga.sk_customer = f.sk_customer
LEFT JOIN analytics.dim_customers nova
       ON nova.codigo_associado = antiga.codigo_associado
      AND nova.valido_de        = antiga.valido_de;

ALTER TABLE analytics.fact_invoices ADD PRIMARY KEY (codigo_boleto);
CREATE INDEX ix_fact_invoices_emissao ON analytics.fact_invoices (data_emissao);

CREATE TABLE analytics.fact_delinquency_snapshot AS
SELECT
    f.codigo_associado, f.nome_associado, f.cpf_associado,
    f.codigo_situacao_associado, f.descricao_situacao_associado,
    f.codigo_regional_associado, f.nome_regional_associado,
    f.codigo_boleto, f.nosso_numero, f.codigo_situacao_boleto,
    f.descricao_situacao_boleto, f.pago, f.codigo_regional,
    f.nome_regional_boleto, f.mes_referente, f.data_emissao,
    f.data_vencimento_original, f.data_vencimento,
    f.valor_boleto::numeric           as valor_boleto,
    -- date, matching fact_invoices and the model. The legacy typed these two as
    -- text because in this population — invoices still open — they are always
    -- null, so pandas never inferred a date type. Verified empty across all
    -- 262,034 rows before converting.
    f.data_pagamento::date            as data_pagamento,
    f.valor_pagamento::numeric        as valor_pagamento,
    f.data_credito_banco::date        as data_credito_banco,
    f.referente, f.codigo_mgfformapagamento,
    f.codigo_forma_pagamento, f.descricao_forma_pagamento,
    f.tarifa_cobranca_banco::numeric  as tarifa_cobranca_banco,
    f.parcela_paga, f.qtde_parcela, f.descricao_tipo_cobranca_recorrente,
    f.codigo_tipo_boleto, f.descricao_tipo_boleto, f.codigo_conta,
    f.codigo_banco, f.nome_banco, f.agencia, f.conta,
    f.descricao_tipo_baixa_boleto, f.veiculo, f.beneficiario,
    f.codigo_situacao,
    f.dt_referencia,
    f.dias_em_atraso::integer         as dias_em_atraso,
    f.faixa_atraso,

    -- The legacy integer resolved to its version, then forward to the hash.
    nova.sk_customer,

    f.criado_em::timestamptz          as criado_em,
    f.controle_carne, f.parcelado
FROM public.fact_delinquency_snapshot f
LEFT JOIN public.dim_customers antiga
       ON antiga.sk_customer = f.sk_customer
LEFT JOIN analytics.dim_customers nova
       ON nova.codigo_associado = antiga.codigo_associado
      AND nova.valido_de        = antiga.valido_de;

ALTER TABLE analytics.fact_delinquency_snapshot
    ADD PRIMARY KEY (codigo_boleto, dt_referencia);

CREATE INDEX ix_delinquency_dt ON analytics.fact_delinquency_snapshot (dt_referencia);

COMMIT;
