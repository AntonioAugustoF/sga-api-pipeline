-- Phase 4b of the ELT migration: seed analytics.fact_invoices with the history
-- the Python path accumulated, so the incremental model has something to
-- continue rather than something to replace.
--
-- Why this exists: invoice extraction fetches what is new, paid or rescheduled,
-- never the full history. raw.invoices holds 7,580 distinct invoices against the
-- 316,918 in public.fact_invoices. Building the fact from raw alone would drop
-- 98% of the revenue history.
--
-- sk_customer is translated, not copied. Phase 3c replaced the SERIAL surrogate
-- key with the snapshot's hash, so each legacy integer is resolved back to its
-- (codigo_associado, valido_de) version and then forward to the new key. The
-- translation is asserted afterwards by
-- assert_fact_invoices_resolve_the_same_customer_version.
--
-- Monetary columns become numeric here, matching the model. The legacy stored
-- them as double precision, which cannot represent a decimal amount exactly.
--
-- Reversible: nothing writes to public. Deliberately not idempotent — CREATE
-- TABLE fails if the table exists rather than discarding rows merged since.

BEGIN;

DROP TABLE IF EXISTS analytics.fact_invoices;

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

COMMIT;
