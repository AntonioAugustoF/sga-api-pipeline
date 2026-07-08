-- Inadimplência por veículo, atribuída ao responsável ATUAL do veículo
-- (voluntário/regional/cooperativa vigentes hoje em dim_vehicles_current).
--
-- Uso: "quem devo acionar hoje sobre essa inadimplência?" — visão operacional.
-- Reescreve a responsabilidade histórica para quem gerencia o veículo agora;
-- para performance histórica por voluntário, ver vw_delinquency_by_vehicle_historico.sql.
--
-- Grão: (codigo_boleto, dt_referencia, codigo_veiculo)
CREATE OR REPLACE VIEW vw_delinquency_by_vehicle_atual AS
SELECT
    f.codigo_boleto,
    f.dt_referencia,
    f.data_emissao,
    f.data_vencimento,
    f.valor_boleto,
    f.dias_em_atraso,
    f.faixa_atraso,
    f.pago,
    b.codigo_veiculo,
    b.qtd_veiculos_boleto,
    f.valor_boleto / b.qtd_veiculos_boleto AS valor_rateado,
    v.codigo_voluntario,
    v.nome_voluntario,
    v.codigo_regional AS codigo_regional_veiculo,
    v.codigo_cooperativa AS codigo_cooperativa_veiculo,
    v.codigo_situacao AS codigo_situacao_veiculo
FROM fact_delinquency_snapshot f
LEFT JOIN bridge_invoices_vehicles b ON b.codigo_boleto = f.codigo_boleto
LEFT JOIN dim_vehicles_current v ON v.codigo_veiculo = b.codigo_veiculo;
