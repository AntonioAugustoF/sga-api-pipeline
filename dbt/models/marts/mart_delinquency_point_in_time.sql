-- Historical assignment: each row is credited to the volunteer that was responsible
-- for the vehicle on the snapshot reference date. Use to measure past performance
-- without a portfolio change rewriting history.
--
-- The relations are imported as CTEs rather than aliased inline. Under
-- dbt build --empty a relation is replaced by a subquery that already carries
-- its own alias, and a second alias right after it is invalid SQL.
--
-- Reads the dbt models rather than the tables the pandas path writes. Until
-- this changed, the analytics layer still depended on public and the cutover
-- could not begin.

with delinquency as (

    select * from {{ ref('int_delinquency_by_vehicle') }}

), vehicles as (

    select * from {{ ref('dim_vehicles') }}

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
    and d.dt_referencia >= v.valido_de
    and (v.valido_ate is null or d.dt_referencia < v.valido_ate)
