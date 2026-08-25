-- Phase 4c: every (invoice, vehicle) pair and its vehicle count must match the
-- bridge load/load_invoice_vehicle_bridge.py writes.
--
-- valor_rateado is excluded and held to a tolerance instead by
-- assert_bridge_allocation_matches_legacy: the division is exact decimal here
-- and binary floating point there, so 35,890 rows differ by up to 5e-12.
-- qtd_veiculos_boleto is compared exactly, and does match — it is an integer
-- count, and a difference there would mean the explode itself disagreed.

{{ assert_matches_legacy('bridge_invoices_vehicles', 'bridge_invoices_vehicles', [
    'codigo_boleto',
    'codigo_veiculo',
    'qtd_veiculos_boleto'
]) }}
