-- SCD2: each natural key must have exactly one version on effective date
-- Violate this caused the bug which let 1,289 vehicles without current version, with the
-- correspondent revenue without volunteer attribution through weeks.
select codigo_veiculo
from {{ source('warehouse', 'dim_vehicles') }}
group by codigo_veiculo
having count(*) filter (where vigente) <> 1