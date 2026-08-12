-- Historical assignment: each row is credited to the volunteer that was responsible
-- for the vehicle on the snapshot reference date. Use to measure past performance
-- without a portfolio change rewriting history.

select
    d.*,
    v.sk_vehicle,
    v.codigo_voluntario,
    v.nome_voluntario,
    v.codigo_regional as codigo_regional_veiculo,
    v.codigo_cooperativa as codigo_cooperativa_veiculo,
    v.codigo_situacao as codigo_situacao_veiculo
from {{ ref('int_delinquency_by_vehicle') }} d
left join {{ source('warehouse', 'dim_vehicles') }} v
    on v.codigo_veiculo = d.codigo_veiculo
    and d.dt_referencia >= v.valido_de
    and (v.valido_ate is null or d.dt_referencia < v.valido_ate)