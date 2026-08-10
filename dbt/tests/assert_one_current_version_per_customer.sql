-- Same invariant for customers, which suffered the same bug.
select codigo_associado
from {{ source('warehouse', 'dim_customers') }}
group by codigo_associado
having count(*) filter (where vigente) <> 1
