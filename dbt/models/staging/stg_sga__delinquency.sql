-- One row per delinquency in the most recent extraction batch, with the rules from
-- transform/transform_invoices.py and transform/business_rules.py applied.
--
-- Monetary columns are numeric here, where the legacy table used double
-- precision. That was a known debt: binary floating point cannot represent a
-- decimal amount exactly, and rewriting the model is the only cheap moment to
-- fix it. Reconciliation casts this side back to double precision, so the
-- comparison is made at the legacy's resolution.
--
-- Passed through untouched, matching pandas: nome_associado, controle_carne, parcelado.
--
-- Same payload shape as invoices — the two endpoints return identical keys —
-- but a different population: this one is filtered to codigo_situacao 2, the
-- open invoices that make up the delinquency snapshot.


with latest_batch as (

    select payload, _extracted_at
    from {{ source('sga', 'delinquency') }}
    where _extracted_at = (select max(_extracted_at) from {{ source('sga', 'delinquency') }})

)

select
    {{ clean_json_string('codigo_associado') }}                   as codigo_associado,
    payload ->> 'nome_associado'                     as nome_associado,
    {{ clean_json_string('cpf_associado') }}                      as cpf_associado,
    {{ clean_json_string('codigo_situacao_associado') }}          as codigo_situacao_associado,
    {{ clean_json_string('descricao_situacao_associado') }}       as descricao_situacao_associado,
    {{ clean_json_string('codigo_regional_associado') }}          as codigo_regional_associado,
    {{ clean_json_string('nome_regional_associado') }}            as nome_regional_associado,
    {{ clean_json_string('codigo_boleto') }}                      as codigo_boleto,
    {{ clean_json_string('nosso_numero') }}                       as nosso_numero,
    {{ clean_json_string('codigo_situacao_boleto') }}             as codigo_situacao_boleto,
    {{ clean_json_string('descricao_situacao_boleto') }}          as descricao_situacao_boleto,
    {{ clean_json_string('pago') }}                               as pago,
    {{ clean_json_string('codigo_regional') }}                    as codigo_regional,
    {{ clean_json_string('nome_regional_boleto') }}               as nome_regional_boleto,
    {{ clean_json_string('mes_referente') }}                      as mes_referente,
    {{ try_json_cast('data_emissao', 'date') }}                       as data_emissao,
    {{ try_json_cast('data_vencimento_original', 'date') }}           as data_vencimento_original,
    {{ try_json_cast('data_vencimento', 'date') }}                    as data_vencimento,
    {{ try_json_cast('valor_boleto', 'numeric') }}                       as valor_boleto,
    {{ try_json_cast('data_pagamento', 'date') }}                     as data_pagamento,
    {{ try_json_cast('valor_pagamento', 'numeric') }}                    as valor_pagamento,
    {{ try_json_cast('data_credito_banco', 'date') }}                 as data_credito_banco,
    {{ clean_json_string('referente') }}                          as referente,
    {{ clean_json_string('codigo_mgfformapagamento') }}           as codigo_mgfformapagamento,
    {{ clean_json_string('codigo_forma_pagamento') }}             as codigo_forma_pagamento,
    {{ clean_json_string('descricao_forma_pagamento') }}          as descricao_forma_pagamento,
    {{ try_json_cast('tarifa_cobranca_banco', 'numeric') }}              as tarifa_cobranca_banco,
    {{ try_json_cast('parcela_paga', 'bigint') }}                       as parcela_paga,
    {{ try_json_cast('qtde_parcela', 'bigint') }}                       as qtde_parcela,
    {{ clean_json_string('descricao_tipo_cobranca_recorrente') }} as descricao_tipo_cobranca_recorrente,
    {{ clean_json_string('codigo_tipo_boleto') }}                 as codigo_tipo_boleto,
    {{ clean_json_string('descricao_tipo_boleto') }}              as descricao_tipo_boleto,
    {{ clean_json_string('codigo_conta') }}                       as codigo_conta,
    {{ clean_json_string('codigo_banco') }}                       as codigo_banco,
    {{ clean_json_string('nome_banco') }}                         as nome_banco,
    {{ clean_json_string('agencia') }}                            as agencia,
    {{ clean_json_string('conta') }}                              as conta,
    {{ clean_json_string('descricao_tipo_baixa_boleto') }}        as descricao_tipo_baixa_boleto,
    {{ clean_json_string('codigo_situacao') }}                    as codigo_situacao,
    {{ try_json_cast('controle_carne', 'bigint') }}                     as controle_carne,
    payload ->> 'parcelado'                          as parcelado,

    -- flatten_single_value_lists: a one-element list becomes the element itself,
    -- an empty one becomes null.
    payload -> 'beneficiario' ->> 0 as beneficiario,

    -- join_list_columns: the vehicle list is serialised for relational storage.
    -- The exploded form lives in the bridge, not here.
    (
        select string_agg(value, ',')
        from jsonb_array_elements_text(payload -> 'veiculo')
    ) as veiculo,

    _extracted_at
from latest_batch
