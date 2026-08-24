-- Current assignment: each row is credited to the volunteer responsible for
-- the vehicle today, regardless of when the invoice was issued. Use for:
-- "whose portfolio is this right now?"
--
-- Join dim_vehicles filtering by the active record instead of the dim_vehicles_current view,
-- to avoid depending on a database object outside of version control.
--
-- The relations are imported as CTEs rather than aliased inline. Under
-- dbt build --empty a relation is replaced by a subquery that already carries
-- its own alias, and a second alias right after it is invalid SQL.

with delinquency as (

    select * from {{ ref('int_delinquency_by_vehicle') }}

), vehicles as (

    select * from {{ source('warehouse', 'dim_vehicles') }}

)

select
    d.*,
    v.sk_vehicle,
    v.codigo_voluntario,
    v.nome_voluntario,
    v.codigo_regional as codigo_regional_veiculo,
    v.codigo_cooperativa as codigo_cooperativa_veiculo,
    v.codigo_situacao as codigo_situacao_veiculo
from delinquency d
left join vehicles v
    on v.codigo_veiculo = d.codigo_veiculo
    and v.vigente
