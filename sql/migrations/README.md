# Migrations

Applied by hand, once, in order. Nothing records which ones ran, so read this
before running any of them.

| File | Status | Re-running it |
|---|---|---|
| `001`–`009` | Applied before or during the cutover (2026-08). | **Never.** Several start with `DROP TABLE IF EXISTS analytics.<history table>` and rebuild from `public`. With `public` gone they fail; with it present they silently roll months of history back to the legacy copy. Kept as a record of how the history got here. |
| `010_split_invoice_aging_into_view.sql` | Applied 2026-11-27. | Safe: idempotent, each step checks the state it expects. Run before the first `dbt build` containing `models/marts/fact_invoices_base.sql`. |

Raw DDL (`sql/ddl/010_raw_schema.sql`) is `CREATE ... IF NOT EXISTS` and can be
re-applied at any time; CI applies it to a fresh container on every run.
