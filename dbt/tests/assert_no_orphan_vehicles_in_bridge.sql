{{ config(error_if = '>1' )}}

-- Any vehicle being charged must exist on dimension. An orphan is
-- a revenue which no volunteer receive — because of this the days 19/20/21
-- missed the statuses on origin list manifested on BI.
--
-- A known orphan is tolerated: vehicle 3738, a remnant from before the
-- situation list fix. The contract is the limit — this debt cannot
-- grow, and the second orphan breaks the build
--
-- The sources are imported as CTEs rather than aliased inline. Under
-- dbt build --empty a source is replaced by a subquery that already carries
-- its own alias, and a second alias right after it is invalid SQL.

with bridge as (

    select * from {{ source('warehouse', 'bridge_invoices_vehicles') }}

), vehicles as (

    select * from {{ source('warehouse', 'dim_vehicles') }}

)

select b.codigo_veiculo
from bridge b
left join vehicles v
    on v.codigo_veiculo = b.codigo_veiculo
    and v.vigente
where v.codigo_veiculo is null
group by b.codigo_veiculo
