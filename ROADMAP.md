# Roadmap — ETL to ELT Migration

A living document. It records the design of the migration from the current
architecture (business rules in pandas, explicit loading in Python) to ELT
(Python only lands raw data; dbt produces dimensions and facts).

Restore point: tags `v1.0.0-etl` and `v1.0.1-etl`, plus a full dump under
`C:\backups\`. Any phase can be abandoned without loss.

---

## 1. Migration principle

**Nothing is deleted before it is reconciled.** Every migrated entity runs in
parallel with the current pipeline until a test compares the two tables row by
row and passes. Only then is the old path removed.

This is why the migration is slow, and it is why it is safe. The warehouse
serves Power BI in production; there is no window for "let's see if it works".

**Build order is not cutover order.** SCD2 is the riskiest part, but facts
depend on dimensions — so the snapshots are *built* early (Phase 3) and *cut
over* late (Phase 5), running in parallel the whole time.

---

## 2. Current state to target state

| Today | Target |
|---|---|
| `extract/*.py` → JSON in `data/raw/` | `extract/*.py` → `raw.<entity>` (append-only jsonb) |
| `transform/*.py` (8 files, business rules in pandas) | `dbt/models/staging/` + `dbt/models/intermediate/` |
| `load/scd2.py` (hand-rolled SCD2) | `dbt snapshot` |
| `load/load_dimensions.py`, `load_facts.py` | `dbt/models/marts/` materialized as `table` |
| `load/load_invoice_vehicle_bridge.py` | a model under `intermediate/` |
| `infra/sync_table_schema` alters production | dbt owns the schema; the function is deleted |
| Power BI reads `public` | Power BI reads `analytics` |

Prefect remains the orchestrator. The flow shrinks to `extract → dbt build`.

---

## 3. Phases

### Phase 0 — Raw landing layer ✅

**Goal:** have a place where raw data lands without any rule applied to it.

**Delivered**
- Schema `raw` in PostgreSQL, versioned in `sql/ddl/010_raw_schema.sql`.
- One table per entity: `_extracted_at timestamptz`, `_endpoint text`,
  `payload jsonb`.
- A generic writer in `infra/raw_writer.py`, shared by all nine entities.

**Decisions locked in**
- `payload` is the whole JSON, unflattened. Flattening is transformation.
- Append-only. This is what allows any past day to be reprocessed without
  re-extracting, and it is the property that actually defines ELT — not the
  tooling.
- `assert_extraction_complete` still runs **before** the write. A partial
  extraction never reaches `raw`.
- The batch timestamp is generated once per write, not per row, and the insert
  runs in a single transaction. A `max(_extracted_at)` filter in staging can
  therefore never select a truncated batch.

**Completed** 2026-08-18. All nine tables land on the daily run, in parallel
with the existing pipeline, with no change to its behaviour. `raw.customers`
and `raw.vehicles` already reconcile against the production dimensions
(11,100 and 17,948 rows).

---

### Phase 1 — Pilot: `dim_regionals` ✅

**Goal:** prove the end-to-end pattern on the entity that is cheapest to get
wrong.

**Deliverables**
- `staging/stg_sga__regionals.sql` — flattens the jsonb, casts, renames.
- `marts/dim_regionals.sql` — materialized as `table`.
- A singular test comparing `analytics.dim_regionals` against
  `public.dim_regionals` row by row.
- The dbt naming convention and folder structure, fixed here in writing.

**Done when:** the reconciliation test passes on two consecutive daily runs.
The old path is **not** removed in this phase.

**Risk:** low. Few rows, no SCD2, no dependents.

**Completed** 2026-08-21. The reconciliation test returns zero rows and has done so
against separate daily production writes. The pandas path still runs and still
writes `public.dim_regionals`.

---

### Phase 2 — Remaining simple dimensions ✅

`dim_cooperatives`, `dim_statuses`, `dim_status_invoice`, `dim_volunteers`.

Repeats the Phase 1 pattern. No new architectural decisions — this is volume of
work, not of judgement. It is where the first Jinja macros appear, once the
repetition between staging models becomes obvious.

**Done when:** all of them reconcile.

**Completed** 2026-08-24. All four reconcile against production data. Two
warnings stand by design: the known orphan vehicle and the two inferred
cooperatives, both of which fail the build if they grow.

---

### Phase 3 — SCD2 via `dbt snapshot`

`dim_vehicles` and `dim_customers`. The most important phase in this roadmap,
and the only one that moves *history keeping* rather than transformation.

**Why it matters:** the stranded-version bug (1,289 vehicles and 565 customers
whose `valido_ate` was closed and never reopened, stranding R$ 11M of
attribution) happened because closing a version and opening the next were two
separate statements, and the second depended on a set recomputed after the
first. `load/scd2.py` works around it today by materialising `_changed_` up
front, with a comment explaining the danger. A snapshot does both sides in one
MERGE, so the bug is not fixed — it becomes unrepresentable.

**What makes this phase different:** `dim_regionals` can be dropped and rebuilt
from the API tomorrow. `dim_vehicles` cannot. The API returns current state
only, so the 3,136 historical vehicle versions and 1,684 customer versions exist
nowhere else. They were accumulated one day at a time over months of operation
and are the hardest asset in the project to replace.

**Four things `dbt snapshot` does not do**, all of which `load/scd2.py` does:

1. *Reproduce existing history.* A fresh snapshot starts empty and builds
   forward. The history has to be transplanted.
2. *Refresh non-monitored columns in place.* `scd2.py` updates unmonitored
   attributes on the open version without opening a new one. With `check_cols`,
   anything off the list freezes at its captured value.
3. *Reach back before first capture.* `EPOCH_DATE = 1900-01-01` makes a new
   key's first version cover facts that predate its discovery. dbt stamps
   `dbt_valid_from` at snapshot time, so an invoice issued before a vehicle was
   first seen would resolve to no version at all.
4. *Maintain integer surrogate keys.* `sk_vehicle` and `sk_customer` are SERIAL
   and referenced by 316,833 fact rows. dbt generates `dbt_scd_id`, an md5 hash.

**Design decisions**

- **Snapshot only the monitored columns.** Descriptive attributes are joined
  from current state at the mart layer. This resolves point 2 and is the
  cleaner dimensional answer anyway: versioning an address was never intended.
- **Surrogate key becomes a deterministic hash** of (natural key,
  `valido_de`). Stable across rebuilds and machines, no sequence to maintain.
  This is the one change in the whole migration visible outside the repository:
  **Power BI has to rebuild the relationship once.**
- **The EPOCH rule moves to the mart** as a window function over each key's
  first version.
- `vigente` disappears as a stored column. In the snapshot model it is a
  consequence of `dbt_valid_to is null`, not a fact to keep in sync.

**Sub-phases**, each its own pull request:

- **3a — Transplant the history.** Populate the snapshot table from
  `public.dim_vehicles` and `dim_customers`, deriving `dbt_scd_id`,
  `dbt_valid_from` and `dbt_valid_to`. No dbt yet. Reconciled on version counts
  and timeline coverage. Writes to a new table, so a failure loses nothing.
- **3b — Run the snapshot.** `dbt snapshot` continues from where the transplant
  stopped. Runs in parallel for several days with a test comparing open versions
  on both sides.
- **3c — The mart models.** `dim_vehicles` and `dim_customers` over the
  snapshot, applying the hash surrogate key, the EPOCH rule and the join of
  non-monitored attributes.

**Done when:** both reconcile and the `assert_one_current_version_per_*` tests
pass against `analytics`.

**Risk:** high. History corrupted here cannot be recovered from the API. The
dump under `C:\backups\` is the only net.

---

### Phase 4 — Facts, bridge and delinquency

`fact_invoices`, `int_invoice_vehicle_bridge`, `fact_delinquency_snapshot`.

**Deliverables**
- Facts built on top of the Phase 3 snapshots.
- The bridge as an `intermediate/` model, keeping the existing fan-out test.
- The current delinquency models (`int_delinquency_by_vehicle`,
  `mart_delinquency_*`) repointed from `source('warehouse', ...)` to `ref()`.

**Debts addressed in this phase** (see §5):
- `data_referencia` comes from the data, not from the run date.
- Monetary columns typed `NUMERIC` — rewriting the models is the only cheap
  moment to do this.
- `valor_pagamento` given one consistent type across `fact_invoices` and
  `fact_delinquency_snapshot`.

**Done when:** the facts reconcile and the known 46-boleto divergence (§5) still
covers exactly those 46 — no more, no fewer.

---

### Phase 5 — Cutover

**Deliverables**
- Power BI repointed to `analytics`, via `mart_delinquency_point_in_time` and
  the other marts.
- `transform/` and `load/` deleted.
- `infra/sync_table_schema` deleted — dbt becomes the schema owner.
- The Prefect flow reduced to `extract → dbt build`.
- `infra/freshness.py` pointed at the `analytics` tables.
- `sql/ddl/000_baseline.sql` regenerated.
- Tag `v2.0.0-elt`.

**Done when:** a full day runs without the old code and the dead-man's switch
stays quiet.

---

## 4. Optional phases (post-migration)

Independent of each other. None blocks the others.

**A — dbt in CI.** ✅ A throwaway PostgreSQL service container on the runner,
created from the versioned DDL, running `dbt build --empty`: every model and
test reaches a real database with `limit 0`, so the SQL is validated without any
fixture to maintain.

DuckDB was the original plan and was the wrong call. The staging layer uses
`pg_input_is_valid` and `at time zone`, neither of which DuckDB shares, so a
green DuckDB build would say nothing about the SQL that runs in production. The
same-dialect container is both more faithful and simpler — no second target in
`profiles.yml`.

This only partly answers issue #9. The build runs; the data assertions still do
not, because `--empty` makes every test pass vacuously. Seeding fixtures into
`raw` and `public` is the next increment.

**B — BigQuery.** A third target. The free tier (10 GB storage, 1 TB queried per
month) is far above the current volume of ~191k rows. The exercise is precisely
to demonstrate that, with dbt, changing warehouse means changing `profiles.yml`
and fixing dialect-specific SQL.

**C — `dlt` (dlthub).** Replaces the hand-written Phase 0 writer with an EL
library that does schema inference and incremental loading. Only worth doing
once the raw layer is stable — replacing the implementation of something that
works is cheap; replacing the design is not.

**D — `dbt docs generate` + exposures.** Documents lineage all the way to Power
BI. High portfolio value, low cost.

---

## 5. Known facts the migration must preserve

A record of what has already been investigated, so it is not re-discovered as if
it were a new bug during reconciliation.

- **46 divergent boletos** between `fact_delinquency_snapshot.valor_boleto` and
  `fact_invoices.valor_boleto` (293 of 191,255 rows, 0.39%). The ratios cluster
  at 0.5, 2.0 and sevenths; for 29 of the 46 the most recent snapshot agrees
  with `fact_invoices` again. **Conclusion: legitimate history-versus-current
  behaviour, not corruption.** Phase 4 reconciliation must find exactly these 46.
- **Orphan vehicle `3738`** in the bridge. Covered by
  `assert_no_orphan_vehicles_in_bridge` with `error_if: '>1'`.
- **Cooperatives `37` and `65` exist only as hand-written rows.** They were
  inserted directly into `public.dim_cooperatives` to unblock a foreign key —
  three customers and two vehicles reference them — and carry null audit
  columns plus an unnormalised, misspelt name (`Cooperativa excluida da base`,
  no accent). No code reproduced them, so rebuilding from the baseline would
  have broken the constraint. Phase 2 replaced the patch with a derived rule in
  `int_cooperatives_inferred`: any cooperative referenced by a customer or
  vehicle but absent from the API. The misspelling is reproduced verbatim on
  purpose and should be fixed at cutover, when there is no legacy table left to
  match.
- **`sql/ddl/000_baseline.sql` could not be replayed onto an empty database.**
  `pg_dump -n public` emits `CREATE SCHEMA public`, which every new database
  already has, so the restore point failed on line 25 the first time anything
  tried to use it — discovered when CI applied it to a fresh container. CI drops
  the schema first; the dump is left untouched, because regenerating it would
  silently reinstate the line. Worth remembering if the baseline is ever needed
  for an actual restore.
- **Thirty customers carry impossible dates.** Birth years such as 2972, 7973
  and 9975, and birth dates in the future that yield a negative age. The pandas
  path made them invisible rather than reporting them: `datetime64[ns]` spans
  only 1677 to 2262, so `to_datetime(errors="coerce")` returned NaT and the
  warehouse stored NULL. `stg_sga__customers` keeps what the source actually
  said and `assert_customer_dates_are_plausible` reports it, warning at one and
  failing at thirty-one. None of the affected columns is monitored, so none
  affects SCD2 versioning.
- **`campos_opcionais` holds a leaked Python repr.** The pandas path calls
  `str()` on a list, so the warehouse stores
  `['sem campo opcional cadastrado']` with single quotes. The dbt model emits
  real JSON and the column is excluded from reconciliation on purpose.
- **Monetary columns are `double precision`.** The rateio reconstruction error
  sits around 1e-13, far below the 0.005 tolerance — not urgent, but Phase 4 is
  the cheap moment to fix it.
- **`data_referencia` uses the run date**, not the date of the data. Fixed in
  Phase 4.
- **Python is installed per-user (HKCU).** Three production entry points depend
  on the absolute path to `python.exe`. Any environment change during the
  migration has to account for this.

---

## 6. Tracking

| Phase | Scope | Status |
|---|---|---|
| 0 | Raw landing layer | **done** — 9 tables, 2026-08-18 |
| 1 | Pilot `dim_regionals` | **done** — 2026-08-21 |
| 2 | Simple dimensions | **done** — 2026-08-24 |
| 3 | SCD2 via `dbt snapshot` | in progress |
| 4 | Facts, bridge, delinquency | not started |
| 5 | Cutover | not started |
| A | dbt in CI | **done** — 2026-08-21 |
| B–D | Optional | not started |
