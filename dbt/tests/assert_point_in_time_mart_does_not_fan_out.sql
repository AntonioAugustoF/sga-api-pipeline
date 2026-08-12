-- The point-in-time join matches one version per date. If two versions of the same key
-- cover the same date — overlapping windows — the row duplicates and the value is counted
-- twice. This exact type of duplication was showed up in Power BI.
select dt_referencia, codigo_boleto, codigo_veiculo
from {{ ref('mart_delinquency_point_in_time') }}
group by dt_referencia, codigo_boleto, codigo_veiculo
having count(*) > 1