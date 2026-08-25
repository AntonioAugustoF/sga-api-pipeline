-- Phase 4d: seed analytics.fact_delinquency_snapshot with the 38 daily
-- snapshots the Python path recorded from 2026-07-01 onward. raw.delinquency
-- only begins on 2026-08-18, so the earlier days exist nowhere else — a daily
-- photograph cannot be retaken.
--
-- Monetary columns become numeric, matching the model. valor_pagamento was
-- bigint here and double precision in fact_invoices, the type inconsistency the
-- roadmap has carried since the start; both are numeric from now on.
--
-- Reversible: nothing writes to public. Deliberately not idempotent.

BEGIN;

DROP TABLE IF EXISTS analytics.fact_delinquency_snapshot;

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
