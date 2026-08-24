-- Exactly one open version per natural key, on both snapshots.
--
-- This is the invariant the stranded-version bug broke: 1,289 vehicles and 565
-- customers were closed and never reopened, so they had zero open versions and
-- R$ 11M of attribution resolved to nothing. A snapshot closes and opens in one
-- MERGE, which is why the bug is unrepresentable here — this test exists to
-- prove that claim rather than assume it.

select 'snap_vehicles' as tabela, codigo_veiculo as chave, count(*) as abertas
from {{ ref('snap_vehicles') }}
where dbt_valid_to is null
group by 1, 2
having count(*) <> 1

union all

select 'snap_customers', codigo_associado, count(*)
from {{ ref('snap_customers') }}
where dbt_valid_to is null
group by 1, 2
having count(*) <> 1
