{% snapshot snap_customers %}

{#-
  hard_deletes is declared rather than inherited. 'ignore' leaves a natural key
  absent from the source open, which matches load/scd2.py: extraction can be
  partial, so absence is never a business change.

  It is also what makes `dbt build --empty` safe to run against the production
  warehouse, since --empty feeds the snapshot an empty source. Setting this to
  'invalidate' would close every open version on the next such run.
-#}

{{
    config(
        target_schema = 'analytics',
        unique_key = 'codigo_associado',
        hard_deletes = 'ignore',
        strategy = 'check',
        check_cols = [
            'codigo_situacao',
            'codigo_voluntario',
            'codigo_classificacao',
            'codigo_regional',
            'codigo_cooperativa',
        ],
    )
}}

select
    codigo_associado,
    codigo_situacao,
    codigo_voluntario,
    codigo_classificacao,
    codigo_regional,
    codigo_cooperativa
from {{ ref('stg_sga__customers') }}

{% endsnapshot %}
