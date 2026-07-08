-- Inadimplência por veículo, atribuída ao responsável do veículo NA DATA do
-- snapshot (dt_referencia) — resolve a versão SCD2 de dim_vehicles vigente
-- naquele dia, em vez de sempre puxar a versão atual.
--
-- Uso: performance histórica por voluntário — quem era responsável pelo
-- veículo quando aquela inadimplência foi medida, preservando a atribuição
-- mesmo que o veículo tenha trocado de voluntário/regional depois.
--
-- Ancorado em dt_referencia (dia do snapshot), não em data_emissao do boleto:
-- a pergunta é "quem gerenciava esse veículo enquanto ele seguia em atraso",
-- não "quem vendeu o contrato originalmente". Ajuste a ancoragem se a
-- necessidade de negócio for a segunda.
--
-- Grão: (codigo_boleto, dt_referencia, codigo_veiculo)
CREATE OR REPLACE VIEW vw_delinquency_by_vehicle_historico AS
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
    v.sk_vehicle,
    v.codigo_voluntario,
    v.nome_voluntario,
    v.codigo_regional AS codigo_regional_veiculo,
    v.codigo_cooperativa AS codigo_cooperativa_veiculo,
    v.codigo_situacao AS codigo_situacao_veiculo
FROM fact_delinquency_snapshot f
LEFT JOIN bridge_invoices_vehicles b ON b.codigo_boleto = f.codigo_boleto
LEFT JOIN dim_vehicles v
    ON v.codigo_veiculo = b.codigo_veiculo
    AND f.dt_referencia >= v.valido_de
    AND (v.valido_ate IS NULL OR f.dt_referencia < v.valido_ate);
