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

**Completed** 2026-08-28, after being recorded as complete on the 24th with
only three of its four dimensions built. Nothing caught that: there is no test
for a model that does not exist, and `dbt build` validates what is there.

`dim_volunteers` turned out to be more than a missing file. It was the first
entity where the API stopped returning members, which exposed a semantics
difference that had been invisible until then: `load_dimensions.py` upserts and
never deletes, so the legacy dimension accumulates every key it has ever seen,
while a `table` materialisation rebuilds from current state. Four volunteers
referenced by thirteen vehicles and 204 invoices would have been dropped.

All five simple dimensions are therefore incremental, seeded by
`sql/migrations/005_transplant_simple_dimensions.sql`, and the customer and
vehicle staging models select the latest known row per key rather than the keys
in the latest batch.

---

### Phase 3 — SCD2 via `dbt snapshot` ✅

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

- **3a — Stage the two entities.** ✅ 2026-08-24. `stg_sga__vehicles` and
  `stg_sga__customers`, reconciled against the current version of both
  dimensions. This was a prerequisite the original plan missed: a monitored
  column normalised differently here would make the first snapshot run see a
  change on every row.
- **3b — Transplant the history and start the snapshot.** ✅ 2026-08-24.
  `sql/migrations/001_transplant_scd2_history.sql` copies all 33,870 versions
  into snapshot-shaped tables; `dbt snapshot` then ran and inserted **zero**
  rows, which is the proof that staging matches the transplanted open versions
  exactly. Both timelines are compared in full on every build.
- **3c — The mart models.** ✅ 2026-08-24. `dim_vehicles` and `dim_customers`
  over the snapshots, as mixed dimensions: the monitored columns are Type 2 and
  come from the snapshot, every descriptive attribute is Type 1 and joined from
  current state. The surrogate key is the snapshot's own `dbt_scd_id`, already a
  deterministic hash of the natural key and the version's start. Current
  versions reconcile in full against `public`.

**Done when:** both reconcile and the `assert_one_current_version_per_*` tests
pass against `analytics`.

**Risk:** high. History corrupted here cannot be recovered from the API. The
dump under `C:\backups\` is the only net.

---

### Phase 4 — Facts, bridge and delinquency

`fact_invoices`, `bridge_invoices_vehicles`, `fact_delinquency_snapshot`.

**What this phase turned out to be about.** The plan treated facts as ordinary
models. They are not: all three *accumulate*. Extraction fetches what is new,
paid or rescheduled, never the full history, so the raw layer holds 7,580
invoices against 316,918 in the fact and 39 daily snapshots exist where raw
covers a week. Every one of them needs the same treatment phase 3 needed —
incremental materialisation plus a transplant — and none can be rebuilt from
source. A table materialisation would have dropped 98% of the revenue history
with every test still green.

**Debts closed here** (see §5): `data_referencia` now comes from the data rather
than the run date; monetary columns are `numeric`; `valor_pagamento` and
`dias_em_atraso` have one consistent type across both facts, as do
`data_pagamento` and `data_credito_banco`.

**Sub-phases**, each its own pull request:

- **4a — Stage invoices.** ✅ 2026-08-25. `stg_sga__invoices`, with the five
  business rules from `transform/business_rules.py` expressed in SQL.
- **4b — `fact_invoices` incremental.** ✅ 2026-08-25. All 316,918 invoices
  reconcile across 46 columns.
- **4c — The bridge.** ✅ 2026-08-25. 382,755 pairs; `qtd_veiculos_boleto`
  exact, `valor_rateado` within 5e-12.
- **4d — `fact_delinquency_snapshot`.** ✅ 2026-08-25. 262,034 rows over 39 days,
  reconciling exactly on all 44 compared columns with no tolerance needed
  anywhere.
- **4e — Repoint the delinquency models.** ✅ 2026-08-25, in the same pull
  request as 4d. `int_delinquency_by_vehicle` and `mart_delinquency_*` read
  `ref()`. Every model now reads either `source('sga')` or another model, so
  the `warehouse` source survives only in the reconciliation tests — which is
  where it belongs, and what makes phase 5 removable in one step.

**Done when:** the facts reconcile, nothing in `analytics` reads from `public`,
and the value-drift set (§5) is identical on both sides.

---

### Phase 5 — Cutover ✅ 2026-08-29

Done in one pass rather than after the planned few days of parallel running.
The waiting period was worth something concrete — reconciliation had never
seen a month turn — and it was skipped deliberately, with a verified backup
(`sga_warehouse_2026-08-29.dump`) and the tag `v1.1.0-pre-cutover` marking the
last commit where both paths existed.

**Delivered**
- Power BI repointed to `analytics`. Done first: while the dashboard still
  read `public`, deleting the loaders would have frozen it in silence.
- The 22 reconciliation tests, the four `assert_*_matches_legacy` macros and
  the `warehouse` source removed. Two tests that read `public` were never
  reconciliation and stayed: `assert_no_orphan_vehicles_in_bridge`, repointed
  to `ref()`, and `assert_customer_dates_are_plausible`, already on `ref()`.
- `transform/` (9 modules) and `load/` (5, `sync_table_schema` included)
  deleted, with `infra/loader.py`, `infra/transformations.py` and
  `infra/identifiers.py`, which existed only to serve them.
- The Prefect flow reduced to `extract → dbt build`.
- Extractors stopped writing `data/raw/*.json`. Nothing had read those files
  since `infra.loader` was deleted, and a directory filling with dated JSON
  reads like a live data path.
- `infra/freshness.py` pointed at `analytics` — not a schema rename, see §5.
- `sql/ddl/000_baseline.sql` **deleted rather than regenerated**. `raw` is the
  only schema still created by hand and `010_raw_schema.sql` already is its
  DDL; a versioned description of `analytics` would duplicate what dbt owns.
- pandas, pyarrow and numpy dropped from `requirements.txt`.
- README rewritten: it described a Transform (Pandas) stage that no longer
  exists.
- `public` **left in place**, no longer written. Dropping the schema is a
  separate decision; it costs only disk and it is the only copy of the
  reference outside the dump.

**Still open:** tag `v2.0.0-elt` after a full unattended night, and drop
`public` once there is no reason to keep it.

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

- **Invoices whose value was revised after a snapshot was taken.** The snapshot
  records what an invoice was worth on a given day; `fact_invoices` records what
  it is worth now, so the two legitimately disagree once a value changes. This
  was recorded as 46 invoices across 293 rows; by 2026-08-25 it was 63 across
  471, and it grows with ordinary business activity. **Legitimate
  history-versus-current behaviour, not corruption.** Phase 4 therefore asserts
  that the dbt models reproduce the legacy's drift set exactly rather than
  pinning a count — a fixed threshold here would fail on normal operation.
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
- **The `public` baseline dump could not be replayed onto an empty database.**
  *(Historical: the file was deleted at the cutover.)*
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
- **`dbt build --empty` must never run against the real warehouse.** dbt writes
  the `limit 0` into the relations themselves, so every view and every table is
  left empty until a normal `dbt build` recreates them. Only snapshots and
  incremental models survive — a snapshot is not rebuilt, and an incremental
  merge from an empty source changes nothing. It ran by mistake during both
  phase 3c and phase 4b, and the
  symptom was misleading: every descriptive column in the marts came back NULL,
  which read like a broken join rather than an empty source. CI is safe because
  its database is a throwaway container.
- **The two paths must run at the same cadence, or reconciliation measures the
  schedule.** The pandas path runs nightly; dbt ran on demand until 2026-08-28.
  Three days of drift collapsed 59 SCD2 transitions into one date, lost two
  entire days of `fact_delinquency_snapshot` (14,057 rows), and left 194
  invoices with a stale `dias_em_atraso`. None of it was recoverable by running
  dbt again — a daily photograph cannot be taken retroactively — so `public` was
  copied back by migrations 006 and 007. `dbt build` now runs inside the Prefect
  flow. This was filed as issue #9 and treated as debt; it was a prerequisite.
- **Running the flow twice in one day makes the two paths disagree, and only
  one of them is wrong.** It happened on 2026-08-28: the nightly run at 03:02
  on the pre-dbt code, then the rebuilt flow by hand at 16:11. The pandas path
  cannot represent a second observation — `valido_de` is a `DATE`, so the
  second change of the day overwrites the first, and
  `load_delinquency_snapshot.py` deletes `dt_referencia` and reinserts it. dbt
  has timestamp grain and merges without deleting, so it recorded both: 25 SCD2
  versions that open and close on the same date, and 58 boletos that were open
  in the morning and settled by the afternoon. dbt kept the more accurate
  record; it was discarded anyway, by migrations 008 and 009, because the
  legacy path is the reference until cutover and a same-date version pair also
  makes the point-in-time joins ambiguous. The unified flow runs once a night,
  so this does not recur on its own — but a manual run on a day the schedule
  already fired reproduces it exactly.
- **`criado_em` on the facts is not a run stamp, and the freshness check must
  not treat it as one.** It sits in `merge_exclude_columns` on purpose, so a row
  keeps the moment it first appeared however many times it is merged afterwards.
  Its maximum is therefore the age of the newest invoice, not of the last run,
  and a quiet day would read as a dead pipeline. `infra/freshness.py` watches
  `dim_customers` and `dim_vehicles` instead — materialised as tables and
  rebuilt in full every run — plus `fact_delinquency_snapshot.dt_referencia`,
  which asserts something stronger than recency: that the photograph for the day
  exists. Read as hours since that date's midnight it lands on the same scale as
  the timestamps, so the 26h limit needed no change.
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
| 3 | SCD2 via `dbt snapshot` | **done** — 2026-08-24 |
| 4 | Facts, bridge, delinquency | **done** — 2026-08-25 |
| 5 | Cutover | **done** — 2026-08-29 |
| A | dbt in CI | **done** — 2026-08-21 |
| B–D | Optional | not started |
