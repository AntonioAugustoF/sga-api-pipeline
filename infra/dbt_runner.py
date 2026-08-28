"""Runs the dbt build from inside the daily flow.

The two paths have to run at the same cadence. The pandas path runs every night;
until this existed, dbt ran only when someone typed the command, and three days
of drift were enough to collapse fifty-nine version transitions into one date —
see sql/migrations/006_resync_scd2_snapshots.sql. Reconciliation that compares a
warehouse written last night against one written last week measures the
schedule, not the models.

dbtRunner is used rather than a subprocess because it returns a structured
result: success, and the list of nodes that failed. A subprocess would give an
exit code and a wall of text to parse.
"""

from pathlib import Path

from dbt.cli.main import dbtRunner

from infra.logger import get_logger

logger = get_logger(__name__)

DBT_DIR = Path(__file__).resolve().parent.parent / "dbt"


class DbtBuildError(RuntimeError):
    """Raised when dbt build finishes with a failing node."""


def run_dbt_build() -> None:
    """Builds every dbt node and raises if any of them fails.

    A failure here stops the flow on purpose, tests included. A failing
    reconciliation test does not corrupt anything by itself — the models were
    already written by the time tests run — but it means the two warehouses
    disagree, and that is precisely the condition this migration exists to catch
    early. Reporting success over it would be the failure mode the project was
    rebuilt to avoid.

    Warnings do not fail the build. Three are expected every night: the known
    orphan vehicle, the two inferred cooperatives, and the thirty customers whose
    birth dates are impossible.
    """
    logger.info("Running dbt build...")

    result = dbtRunner().invoke(
        [
            "build",
            "--project-dir", str(DBT_DIR),
            "--profiles-dir", str(DBT_DIR),
        ]
    )

    if not result.success:
        if result.exception is not None:
            raise DbtBuildError(f"dbt build could not run: {result.exception}") from result.exception

        failed = [
            r.node.name
            for r in getattr(result.result, "results", [])
            if r.status in ("error", "fail", "runtime error")
        ]
        raise DbtBuildError(
            f"dbt build finished with {len(failed)} failing node(s): {', '.join(sorted(failed))}"
        )

    logger.info("dbt build finished successfully.")
