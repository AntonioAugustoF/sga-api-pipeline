{% macro backfill_sk_customer(date_column) %}
    {#-
      Resolves sk_customer for rows that merged before a covering customer
      version existed.

      The point-in-time join runs only for the rows of the current batch, so a
      row that found no version when it merged kept a null key for good — a
      snapshot row is never merged again. On 2026-11-27 that was 82 invoices in
      fact_invoices and 1,422 rows in fact_delinquency_snapshot whose version
      exists today. Only null keys are touched: a resolved key is never
      re-pointed, which is what keeps history stable.

      The ref is wrapped in its own subquery rather than aliased directly:
      under dbt build --empty a ref renders as a subquery that already carries
      an alias, and a second alias after it is invalid SQL.
    -#}
    update {{ this }} as f
    set sk_customer = v.sk_customer
    from (
        select codigo_associado, sk_customer, valido_de, valido_ate
        from {{ ref('dim_customers') }}
    ) as v
    where f.sk_customer is null
      and v.codigo_associado = f.codigo_associado
      and f.{{ date_column }} >= v.valido_de
      and (v.valido_ate is null or f.{{ date_column }} < v.valido_ate)
{% endmacro %}
