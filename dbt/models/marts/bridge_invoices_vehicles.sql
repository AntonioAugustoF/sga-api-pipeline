-- One row per (invoice, vehicle), with the invoice value split evenly across
-- the vehicles it bills, so SUM(valor_rateado) per boleto always reconstructs
-- valor_boleto. Reproduces allocate_invoice_value_by_vehicle.
--
-- Incremental for the same reason as fact_invoices: extraction never returns
-- the full history, so raw covers 7,580 invoices against the 382,755 rows this
-- bridge has accumulated. Seeded by
-- sql/migrations/003_transplant_bridge_invoices_vehicles.sql.
--
-- NEVER run with --full-refresh against the real warehouse.
{{
    config(
        materialized = 'incremental',
        unique_key = ['codigo_boleto', 'codigo_veiculo'],
        incremental_strategy = 'merge',
        merge_exclude_columns = ['criado_em'],
        on_schema_change = 'fail',
    )
}}

with invoices as (

    select codigo_boleto, valor_boleto, veiculo, _extracted_at
    from {{ ref('stg_sga__invoices') }}

), exploded as (

    -- stg_sga__invoices serialises the vehicle list for relational storage;
    -- this is where it is taken apart again. An invoice with no vehicles
    -- contributes no rows, matching the dropna in the pandas version.
    select
        i.codigo_boleto,
        v.codigo_veiculo,
        i.valor_boleto,
        i._extracted_at
    from invoices i
    cross join lateral unnest(string_to_array(i.veiculo, ',')) as v(codigo_veiculo)
    where i.veiculo is not null
      and i.veiculo <> ''

), deduped as (

    -- drop_duplicates on (boleto, veiculo): the same vehicle listed twice on one
    -- invoice must not halve everyone's share.
    select distinct codigo_boleto, codigo_veiculo, valor_boleto, _extracted_at
    from exploded

)

select
    codigo_boleto,
    codigo_veiculo,
    count(*) over (partition by codigo_boleto) as qtd_veiculos_boleto,
    valor_boleto / count(*) over (partition by codigo_boleto) as valor_rateado,

    {{ dbt.current_timestamp() }} as criado_em,
    (_extracted_at at time zone 'America/Sao_Paulo')::date as data_referencia

from deduped
