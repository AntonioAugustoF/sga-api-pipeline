import pandas as pd
from datetime import date as _date
from sqlalchemy import text, inspect
from infra.db_connector import get_db_engine
from infra.logger import get_logger
from load.load_facts import sync_table_schema

logger = get_logger(__name__)

# "Beginning of time" for a natural key's first version. A member discovered today
# may already have facts predating it (the source only started exposing it now), so
# its first version must reach back far enough for those facts to resolve.
EPOCH_DATE = "1900-01-01"


def upsert_scd2_dimension(
    df: pd.DataFrame,
    table_name: str,
    natural_key: str,
    monitored_columns: list[str],
    reference_date,
    surrogate_key: str,
) -> None:
    """Upserts a dimension with SCD Type 2 semantics on `monitored_columns`.

    - New natural keys are inserted as a new current version.
    - Existing natural keys with a change in any monitored column close out
      the current version (vigente=False, valido_ate=reference_date) and open
      a new current version (vigente=True, valido_de=reference_date).
    - Existing natural keys with no monitored change have their non-monitored
      attributes refreshed in place, without opening a new version.
    - Natural keys absent from `df` are left untouched: extraction can be
      partial, so absence is never treated as a business change.
    - Reruns for the same reference_date update that day's version in place
      instead of duplicating it.
    - Natural keys present in `df` but with no current version get one opened,
      which also self-heals rows left without a current version by past runs.
    """
    engine = get_db_engine()
    attr_columns = [c for c in df.columns if c != natural_key]
    all_columns = [natural_key] + attr_columns
    non_monitored = [c for c in attr_columns if c not in monitored_columns]
    temp_table = f"_temp_{table_name}"
    changed_table = f"_changed_{table_name}"

    target_cols_sql = ", ".join(f'"{c}"' for c in all_columns)
    select_cols_sql = ", ".join(f't."{c}"' for c in all_columns)

    with engine.begin() as conn:
        if not inspect(engine).has_table(table_name):
            logger.info(f"Table '{table_name}' not found. Creating SCD2 structure...")
            scd_df = df.copy()
            scd_df["valido_de"] = _date.fromisoformat(EPOCH_DATE)
            scd_df["valido_ate"] = None
            scd_df["vigente"] = True
            scd_df["criado_em"] = pd.Timestamp.now()
            scd_df["atualizado_em"] = pd.Timestamp.now()
            scd_df.to_sql(table_name, conn, if_exists="replace", index=False, chunksize=1000)
            conn.execute(text(f"""
                ALTER TABLE {table_name}
                    ALTER COLUMN valido_de TYPE DATE USING valido_de::date,
                    ALTER COLUMN valido_ate TYPE DATE USING valido_ate::date,
                    ALTER COLUMN vigente    TYPE BOOLEAN USING vigente::boolean
            """))
            conn.execute(text(
                f'ALTER TABLE {table_name} ADD CONSTRAINT uq_{table_name}_nk_validade '
                f'UNIQUE ("{natural_key}", valido_de)'
            ))
            conn.execute(text(
                f'CREATE UNIQUE INDEX uq_{table_name}_vigente ON {table_name} ("{natural_key}") '
                f'WHERE vigente'
            ))
            conn.execute(text(                                                   
                 f'ALTER TABLE {table_name} ADD COLUMN "{surrogate_key}" SERIAL PRIMARY KEY'
            ))
            logger.info(f"Table '{table_name}' created with {len(scd_df)} current-version rows.")
            return

        sync_table_schema(conn, engine, table_name, df)
        # criado_em/atualizado_em are stamped via NOW() in SQL below, not sourced from df,
        # so sync_table_schema (which only compares df's columns) can't add them on its own.
        conn.execute(text(
            f'ALTER TABLE {table_name} '
            f'ADD COLUMN IF NOT EXISTS criado_em TIMESTAMP, '
            f'ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP'
        ))
        df.to_sql(temp_table, conn, if_exists="replace", index=False, chunksize=1000)

        monitored_diff = " OR ".join(f's."{c}" IS DISTINCT FROM c."{c}"' for c in monitored_columns)

        # Materialized before anything is closed: the "changed" set is defined by
        # comparing against the CURRENT version, so re-evaluating it after the
        # UPDATE below would return nothing and the new versions would never be
        # opened, stranding those rows with no current version at all.
        conn.execute(text(f'DROP TABLE IF EXISTS "{changed_table}"'))
        conn.execute(text(f"""
            CREATE TABLE "{changed_table}" AS
            SELECT s."{natural_key}" AS nk
            FROM "{temp_table}" s
            JOIN {table_name} c ON c."{natural_key}" = s."{natural_key}" AND c.vigente
            WHERE {monitored_diff}
        """))

        # Keys with no CURRENT version — covers both brand-new keys and keys left
        # stranded by the bug described above, so a rerun heals them.
        missing_current_cte = f"""
            SELECT s."{natural_key}" AS nk
            FROM "{temp_table}" s
            LEFT JOIN {table_name} c ON c."{natural_key}" = s."{natural_key}" AND c.vigente
            WHERE c."{natural_key}" IS NULL
        """

        closed = conn.execute(text(f"""
            UPDATE {table_name}
            SET vigente = false, valido_ate = :ref_date, atualizado_em = NOW()
            WHERE vigente AND "{natural_key}" IN (SELECT nk FROM "{changed_table}")
        """), {"ref_date": reference_date})
        logger.info(f"Closed {closed.rowcount} outdated version(s) in '{table_name}'.")

        # The new version starts where the previous one ended, so the timeline has no
        # gap a point-in-time lookup could fall into. Covers the three cases at once:
        # a version just closed above resolves to reference_date; a key stranded
        # without a current version resolves to the day it was closed, however long
        # ago; and a brand-new key has no previous version and starts at EPOCH, so
        # facts predating its first appearance still resolve.
        valido_de_sql = f"""
            COALESCE(
                (SELECT MAX(c.valido_ate) FROM {table_name} c
                  WHERE c."{natural_key}" = t."{natural_key}"),
                DATE '{EPOCH_DATE}'
            )
        """

        update_set = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in attr_columns)
        inserted = conn.execute(text(f"""
            INSERT INTO {table_name} ({target_cols_sql}, valido_de, valido_ate, vigente, criado_em, atualizado_em)
            SELECT {select_cols_sql}, {valido_de_sql}, NULL, true, NOW(), NOW()
            FROM "{temp_table}" t
            WHERE t."{natural_key}" IN (
                SELECT nk FROM "{changed_table}" UNION {missing_current_cte}
            )
            ON CONFLICT ("{natural_key}", valido_de) DO UPDATE SET
                {update_set}, vigente = true, valido_ate = NULL, atualizado_em = NOW()
        """), {"ref_date": reference_date})
        logger.info(f"Inserted/refreshed {inserted.rowcount} new version(s) into '{table_name}'.")

        if non_monitored:
            set_clause = ", ".join(f'"{c}" = t."{c}"' for c in non_monitored)
            set_clause += ", atualizado_em = NOW()"
            refreshed = conn.execute(text(f"""
                UPDATE {table_name} d
                SET {set_clause}
                FROM "{temp_table}" t
                WHERE d."{natural_key}" = t."{natural_key}"
                  AND d.vigente
                  AND d."{natural_key}" NOT IN (SELECT nk FROM "{changed_table}")
            """))
            logger.info(f"Refreshed non-monitored attributes on {refreshed.rowcount} unchanged row(s).")

        conn.execute(text(f'DROP TABLE IF EXISTS "{temp_table}"'))
        conn.execute(text(f'DROP TABLE IF EXISTS "{changed_table}"'))
