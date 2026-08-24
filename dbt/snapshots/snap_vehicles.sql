{% snapshot snap_vehicles %}

{#-
  Versions only the monitored columns, matching SCD2_DIMENSIONS in
  load/load_dimensions.py. Descriptive attributes are deliberately absent: with
  the check strategy anything listed here opens a new version when it changes,
  and versioning an address was never the intent. They are joined from current
  state at the mart layer in phase 3c.

  Absent natural keys are left open, which is dbt's default and matches
  load/scd2.py: extraction can be partial, so absence is never a business
  change.
-#}

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
        unique_key = 'codigo_veiculo',
        hard_deletes = 'ignore',
        strategy = 'check',
        check_cols = [
            'codigo_situacao',
            'valor_fixo',
            'codigo_voluntario',
            'data_contrato',
            'codigo_classificacao',
            'codigo_regional',
            'codigo_cooperativa',
            'valor_fipe_protegido',
        ],
    )
}}

select
    codigo_veiculo,
    codigo_situacao,
    valor_fixo,
    codigo_voluntario,
    data_contrato,
    codigo_classificacao,
    codigo_regional,
    codigo_cooperativa,
    valor_fipe_protegido
from {{ ref('stg_sga__vehicles') }}

{% endsnapshot %}
