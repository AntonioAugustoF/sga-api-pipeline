-- One row per invoice, with the derived payment measures and the customer
-- version that was in effect on the issue date. Read through fact_invoices,
-- which adds the aging measures at query time.
--
-- Incremental, not a table, and the distinction is the whole point. Extraction
-- fetches what is new, paid or rescheduled — never the full history — so the
-- raw layer holds a few thousand invoices against the 300k+ this fact has
-- accumulated. Rebuilding from raw would silently replace the warehouse with
-- the last batch and drop 98% of the revenue history while every test stayed
-- green, because each row present would be correct.
--
-- The history was seeded by sql/migrations/002_transplant_fact_invoices.sql and
-- the table renamed from fact_invoices by 010_split_invoice_aging_into_view.sql.
-- NEVER run this model with --full-refresh against the real warehouse: it would
-- reproduce exactly the loss described above.
--
-- Two inputs per run:
--   * int_invoices_latest, the listing batches (invoice windows plus the full
--     open list): whole rows, merged as they come.
--   * stg_sga__invoice_lookups, invoices re-read one by one because they left
--     the open status outside every window. They only correct the status and
--     payment fields (lookup_columns below), on top of the listing row when
--     the invoice is in both, or on top of the row already stored here when it
--     is not — which is the usual case, and the reason the lookup exists.
--
-- criado_em records when a row first appeared and must survive later merges,
-- so it is excluded from the merge update. on_schema_change stops the run when
-- the model and the table disagree, rather than ignoring it silently.
{{
    config(
        materialized = 'incremental',
        unique_key = 'codigo_boleto',
        incremental_strategy = 'merge',
        merge_exclude_columns = ['criado_em'],
        on_schema_change = 'fail',
        post_hook = ["{{ backfill_sk_customer('data_emissao') }}"],
    )
}}

{%- set listing_columns = [
    'codigo_associado', 'nome_associado', 'cpf_associado', 'codigo_situacao_associado',
    'descricao_situacao_associado', 'codigo_regional_associado', 'nome_regional_associado',
    'codigo_boleto', 'nosso_numero', 'codigo_situacao_boleto', 'descricao_situacao_boleto', 'pago',
    'codigo_regional', 'nome_regional_boleto', 'mes_referente', 'data_emissao',
    'data_vencimento_original', 'data_vencimento', 'valor_boleto', 'data_pagamento',
    'valor_pagamento', 'data_credito_banco', 'referente', 'codigo_mgfformapagamento',
    'codigo_forma_pagamento', 'descricao_forma_pagamento', 'tarifa_cobranca_banco',
    'parcela_paga', 'qtde_parcela', 'descricao_tipo_cobranca_recorrente', 'codigo_tipo_boleto',
    'descricao_tipo_boleto', 'codigo_conta', 'codigo_banco', 'nome_banco', 'agencia', 'conta',
    'descricao_tipo_baixa_boleto', 'veiculo', 'beneficiario', 'codigo_situacao',
    'controle_carne', 'parcelado',
] -%}

{%- set lookup_columns = [
    'codigo_situacao_boleto', 'descricao_situacao_boleto', 'pago', 'data_vencimento',
    'valor_boleto', 'data_pagamento', 'valor_pagamento', 'data_credito_banco',
    'descricao_tipo_baixa_boleto', 'parcela_paga', 'codigo_situacao',
] -%}

with listing as (

    -- The invoice windows plus the open invoices they did not bring.
    select {{ listing_columns | join(', ') }}, _extracted_at
    from {{ ref('int_invoices_latest') }}

), lookups as (

    select * from {{ ref('stg_sga__invoice_lookups') }}

), candidates as (

    select * from listing

    {% if is_incremental() %}
    union all

    -- Invoices to correct that the listing did not bring: start from the row
    -- already stored. Its _extracted_at is replaced by the lookup's below.
    select {{ listing_columns | join(', ') }}, null::timestamptz as _extracted_at
    from {{ this }}
    where codigo_boleto in (select codigo_boleto from lookups)
      and codigo_boleto not in (select codigo_boleto from listing)
    {% endif %}

), invoices as (

    select
        {%- for col in listing_columns %}
        {%- if col in lookup_columns %}
        case when l.codigo_boleto is not null then l.{{ col }} else c.{{ col }} end as {{ col }},
        {%- else %}
        c.{{ col }},
        {%- endif %}
        {%- endfor %}
        coalesce(l._extracted_at, c._extracted_at) as _extracted_at
    from candidates c
    left join lookups l
        on l.codigo_boleto = c.codigo_boleto

), customer_versions as (

    select codigo_associado, sk_customer, valido_de, valido_ate
    from {{ ref('dim_customers') }}

)

select
    {%- for col in listing_columns %}
    i.{{ col }},
    {%- endfor %}

    -- classify_payment_status. The null branch reproduces a quirk rather than a
    -- rule: when an invoice is flagged paid but carries no valor_pagamento,
    -- pandas computes NaN, finds abs(NaN) < 0.01 false and NaN < 0 false, and
    -- falls through to pago_a_maior.
    case
        when coalesce(i.pago, '') <> 'y'                          then 'nao_pago'
        when i.valor_pagamento is null or i.valor_boleto is null  then 'pago_a_maior'
        when abs(i.valor_pagamento - i.valor_boleto) < 0.01       then 'pago_integral'
        when i.valor_pagamento - i.valor_boleto < 0               then 'pago_a_menor'
        else 'pago_a_maior'
    end as status_pagamento,

    i.valor_pagamento - i.valor_boleto as diferenca_pagamento,

    -- Point-in-time resolution: the customer version in effect on the issue
    -- date, not the current one. This is what keeps a past invoice credited to
    -- whoever was responsible at the time. Null when no version covers the
    -- date, which is why the epoch rule in dim_customers matters.
    v.sk_customer,

    {{ dbt.current_timestamp() }} as criado_em,

    -- The date of the observation this row reflects, from the data rather than
    -- the run date: the listing batch, or the lookup that corrected the row.
    (i._extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from invoices i
left join customer_versions v
    on v.codigo_associado = i.codigo_associado
   and i.data_emissao >= v.valido_de
   and (v.valido_ate is null or i.data_emissao < v.valido_ate)
