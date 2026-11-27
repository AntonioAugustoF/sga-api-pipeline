{% macro aging_as_of() %}
    {#-
      The date overdue days are measured against when a fact is read rather
      than photographed. Isolated in a macro so unit tests can pin it: a test
      that depends on current_date passes or fails depending on the day it runs.
    -#}
    current_date
{% endmacro %}


{% macro dias_em_atraso(data_vencimento, as_of) %}
    greatest({{ as_of }} - {{ data_vencimento }}, 0)
{% endmacro %}


{% macro faixa_atraso(data_vencimento, as_of) %}
    case
        when {{ data_vencimento }} is null then null
        when {{ dias_em_atraso(data_vencimento, as_of) }} <= 30 then '0-30'
        when {{ dias_em_atraso(data_vencimento, as_of) }} <= 60 then '31-60'
        when {{ dias_em_atraso(data_vencimento, as_of) }} <= 90 then '61-90'
        else '90+'
    end
{% endmacro %}
