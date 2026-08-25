-- Phase 4a: every invoice must match the row load/load_facts.py writes.
--
-- Monetary columns are cast back to double precision on both sides. This model
-- stores them as numeric, which is the fix for a known debt, so the comparison
-- is deliberately made at the legacy's resolution rather than at the model's.
--
-- Two columns are excluded and neither is a modelling difference:
--
--   sk_customer changed meaning in phase 3c, from a SERIAL integer to the
--   snapshot's hash. Comparing the values is impossible; what matters is that
--   both resolve to the same customer version, which
--   assert_fact_invoices_resolve_the_same_customer_version proves directly.
--
--   diferenca_pagamento is the numeric fix showing its work. Subtracting in
--   binary floating point gives 48.88999999999987 where exact decimal
--   arithmetic gives 48.89. Seventy-two invoices differ, all below 1e-12, and
--   assert_payment_difference_matches_legacy holds them to a tolerance.

{{ assert_matches_legacy('fact_invoices', 'fact_invoices', [
    'codigo_associado',
    'nome_associado',
    'cpf_associado',
    'codigo_situacao_associado',
    'descricao_situacao_associado',
    'codigo_regional_associado',
    'nome_regional_associado',
    'codigo_boleto',
    'nosso_numero',
    'codigo_situacao_boleto',
    'descricao_situacao_boleto',
    'pago',
    'codigo_regional',
    'nome_regional_boleto',
    'mes_referente',
    'data_emissao',
    'data_vencimento_original',
    'data_vencimento',
    'valor_boleto::double precision',
    'data_pagamento',
    'valor_pagamento::double precision',
    'data_credito_banco',
    'referente',
    'codigo_mgfformapagamento',
    'codigo_forma_pagamento',
    'descricao_forma_pagamento',
    'tarifa_cobranca_banco::double precision',
    'parcela_paga',
    'qtde_parcela',
    'descricao_tipo_cobranca_recorrente',
    'codigo_tipo_boleto',
    'descricao_tipo_boleto',
    'codigo_conta',
    'codigo_banco',
    'nome_banco',
    'agencia',
    'conta',
    'descricao_tipo_baixa_boleto',
    'veiculo',
    'beneficiario',
    'codigo_situacao',
    'dias_em_atraso::double precision',
    'faixa_atraso',
    'status_pagamento',
    'controle_carne',
    'parcelado'
]) }}
