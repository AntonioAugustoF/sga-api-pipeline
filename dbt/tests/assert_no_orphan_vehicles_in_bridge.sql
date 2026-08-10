{{ config(error_if = '>1' )}}

-- Any vehicle being charged must exist on dimension. An orphan is
-- a revenue which no volunteer receive — because of this the days 19/20/21
-- missed the statuses on origin list manifested on BI.
-- 
-- A known orphan is tolerated: vehicle 3738, a remnant from before the
-- situation list fix. The contract is the limit — this debt cannot
-- grow, and the second orphan breaks the build
select b.codigo_veiculo
from {{ source('warehouse', 'bridge_invoices_vehicles') }} b
left join {{ source('warehouse', 'dim_vehicles') }} v
    on v.codigo_veiculo = b.codigo_veiculo
    and v.vigente
where v.codigo_veiculo is null
group by b.codigo_veiculo