-- The transplanted timeline must stay identical to the one load/scd2.py
-- maintains, for as long as both run in parallel. A divergence here means the
-- two mechanisms disagreed about when a version opened or closed, which is the
-- only failure in this migration that corrupts data the API cannot return.
{{ assert_history_matches_legacy('dim_vehicles', 'dim_vehicles', 'codigo_veiculo') }}
