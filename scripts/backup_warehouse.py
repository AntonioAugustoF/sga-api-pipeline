"""Dumps the analytics schema and verifies the dump can actually be restored.

The tables in analytics hold history that exists nowhere else now that the
pandas path is gone: the SCD2 versions, the invoices and the daily delinquency
snapshots. The API returns current state only, so none of it can be re-derived,
and dbt can rebuild the models but not the history they accumulated.

Verification is the point, not the dump. The old public baseline was treated as
a restore point for weeks and failed on line 25 the first time anything applied
it to an empty database. A dump nobody has restored is a file, not a backup.
"""

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from infra.config import config
from infra.logger import get_logger

logger = get_logger(__name__)

BACKUP_DIR = Path(os.getenv("SGA_BACKUP_DIR", r"C:\backups"))
PROBE_DB = "sga_analytics_restore_probe"

# Relations whose contents cannot be rebuilt from anywhere else. The analytics
# tables carry history transplanted from the pandas path, which predates the raw
# layer; raw carries the API's answers, and the API only ever returns the
# present, so yesterday's response is gone the moment it is not stored.
#
# Views are absent on purpose: dbt recreates them from the models. They are in
# the dump only because they live in the schema.
CRITICAL_TABLES = (
    "analytics.snap_vehicles",
    "analytics.snap_customers",
    "analytics.fact_invoices",
    "analytics.bridge_invoices_vehicles",
    "analytics.fact_delinquency_snapshot",
    "raw.invoices",
    "raw.vehicles",
    "raw.customers",
    "raw.delinquency",
)

# psql and friends are not on PATH in this environment, and the absolute path
# is the same reason infra/freshness.py is scheduled with one: Python is
# installed per user, so anything running as SYSTEM cannot resolve it either.
PG_BIN = Path(os.getenv("SGA_PG_BIN", r"C:\Program Files\PostgreSQL\18\bin"))


class BackupVerificationError(RuntimeError):
    """Raised when a dump exists but does not restore into the expected state."""


def _run(executable: str, *args: str, database: str | None = None) -> str:
    """Runs a PostgreSQL client binary with the project's connection settings.

    The password travels in the child process environment rather than on the
    command line, where it would be visible in the process list to every user
    on the machine.
    """
    command = [
        str(PG_BIN / executable),
        "-h", config.DB_HOST,
        "-p", str(config.DB_PORT),
        "-U", config.DB_USER,
        *( ["-d", database] if database else [] ),
        *args,
    ]
    env = {**os.environ, "PGPASSWORD": config.DB_PASSWORD}
    result = subprocess.run(command, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        raise BackupVerificationError(
            f"{executable} failed with exit code {result.returncode}: {result.stderr.strip()}"
        )
    return result.stdout


def _row_counts(database: str) -> dict[str, int]:
    """Returns the row count of every critical relation."""
    query = " union all ".join(
        f"select '{relation}', count(*) from {relation}" for relation in CRITICAL_TABLES
    )
    output = _run("psql.exe", "-tA", "-F", "|", "-c", query, database=database)
    return {line.split("|")[0]: int(line.split("|")[1]) for line in output.splitlines() if line}


def dump_warehouse(target: Path) -> Path:
    """Writes a custom-format dump of the raw and analytics schemas.

    Both, not just analytics, and for two independent reasons. raw holds the
    API's daily answers, which cannot be re-fetched. And the analytics staging
    views select from raw, so a dump of analytics alone does not restore: the
    first attempt failed on eighteen views for exactly that reason.

    public is deliberately excluded. Everything in it is derived from these two
    and is on its way out in phase 5.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    _run(
        "pg_dump.exe",
        "-n", "raw",
        "-n", "analytics",
        "-Fc",
        "-f", str(target),
        database=config.DB_NAME,
    )
    logger.info(f"Dumped raw and analytics to {target} ({target.stat().st_size / 1_000_000:.1f} MB).")
    return target


def verify_restore(dump_path: Path) -> dict[str, int]:
    """Restores the dump into a throwaway database and compares row counts.

    This is the whole reason the script exists. A dump that has never been
    restored is a file whose contents nobody has checked, and the project has
    already been bitten once by exactly that: the public baseline dump was the
    documented restore point for weeks and failed on its twenty-fifth line the
    first time anything applied it to an empty database.

    The probe database is dropped and recreated on every run, so a stale probe
    can never make a broken dump look good.
    """
    expected = _row_counts(config.DB_NAME)

    _run("psql.exe", "-c", f'DROP DATABASE IF EXISTS "{PROBE_DB}"', database="postgres")
    _run("psql.exe", "-c", f'CREATE DATABASE "{PROBE_DB}"', database="postgres")

    try:
        _run("pg_restore.exe", "-d", PROBE_DB, str(dump_path))
        restored = _row_counts(PROBE_DB)
    finally:
        _run("psql.exe", "-c", f'DROP DATABASE IF EXISTS "{PROBE_DB}"', database="postgres")

    mismatches = {
        table: (expected[table], restored.get(table, 0))
        for table in CRITICAL_TABLES
        if expected[table] != restored.get(table, 0)
    }
    if mismatches:
        detail = "; ".join(f"{t}: expected {e}, restored {r}" for t, (e, r) in sorted(mismatches.items()))
        raise BackupVerificationError(f"Restored state does not match the source. {detail}")

    return restored


def main() -> int:
    dump_path = BACKUP_DIR / f"sga_warehouse_{date.today().isoformat()}.dump"

    try:
        dump_warehouse(dump_path)
        counts = verify_restore(dump_path)
    except BackupVerificationError as e:
        logger.error(f"Backup of the analytics schema failed verification: {e}")
        return 1

    listed = " | ".join(f"{table}: {count}" for table, count in sorted(counts.items()))
    logger.info(f"Backup verified by restoring it. {listed}")
    prune_old_dumps(BACKUP_DIR)
    return 0


# Weekly dumps at ~78 MB each. Eight of them is two months of history for
# roughly 600 MB, which is the trade this project can afford on one disk.
KEEP_LAST = 8


def prune_old_dumps(directory: Path, keep: int = KEEP_LAST) -> list[Path]:
    """Deletes all but the most recent `keep` dumps, newest first.

    Runs only after a dump has been verified, never before. Pruning first would
    mean a failed backup could delete the last good one.
    """
    dumps = sorted(directory.glob("sga_warehouse_*.dump"), reverse=True)
    for stale in dumps[keep:]:
        stale.unlink()
        logger.info(f"Pruned old dump: {stale.name}")
    return dumps[:keep]


if __name__ == "__main__":
    sys.exit(main())
