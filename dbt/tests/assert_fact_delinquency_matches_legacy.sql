-- Phase 4d: every (invoice, reference date) row must match the snapshot
-- load/load_delinquency_snapshot.py writes. All 44 compared columns reconcile
-- exactly across 262,034 rows — no tolerance is needed anywhere, including the
-- monetary ones. numeric and double precision only diverge under arithmetic,
-- and nothing here is computed from them.
--
-- Excluded, and none is a modelling difference:
--
--   sk_customer changed meaning in phase 3c and is proved equivalent by
--   assert_fact_delinquency_resolves_the_same_customer_version.
--
--   data_pagamento and data_credito_banco are text in the legacy table and date
--   here. pandas never inferred a date type because in this population — still
--   open invoices — both columns are null in all 262,034 rows, verified before
--   converting. There is nothing to compare.

{{ assert_matches_legacy('fact_delinquency_snapshot', 'fact_delinquency_snapshot', [
    'codigo_associado', 'nome_associado', 'cpf_associado',
    'codigo_situacao_associado', 'descricao_situacao_associado',
    'codigo_regional_associado', 'nome_regional_associado', 'codigo_boleto',
    'nosso_numero', 'codigo_situacao_boleto', 'descricao_situacao_boleto',
    'pago', 'codigo_regional', 'nome_regional_boleto', 'mes_referente',
    'data_emissao', 'data_vencimento_original', 'data_vencimento',
    'valor_boleto::double precision', 'valor_pagamento::double precision',
    'referente', 'codigo_mgfformapagamento', 'codigo_forma_pagamento',
    'descricao_forma_pagamento', 'tarifa_cobranca_banco::double precision',
    'parcela_paga', 'qtde_parcela', 'descricao_tipo_cobranca_recorrente',
    'codigo_tipo_boleto', 'descricao_tipo_boleto', 'codigo_conta',
    'codigo_banco', 'nome_banco', 'agencia', 'conta',
    'descricao_tipo_baixa_boleto', 'veiculo', 'beneficiario',
    'codigo_situacao', 'dt_referencia', 'dias_em_atraso', 'faixa_atraso',
    'controle_carne', 'parcelado'
]) }}
