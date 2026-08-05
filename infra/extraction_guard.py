"""Refuses to persist an extraction that finished with gaps.

Each extractor iterates over the status list and swallows per-status errors so
that one bad status does not abort the rest. That resilience silently became a 
correctness bug: the run wrote a snapshot missing whole statuses, the load saw a
smaller-but-plausible dataset, and the pipeline reported success. The gap only
surfaced days later, as vehicles with no attribution.
"""

from infra.logger import get_logger

logger = get_logger(__name__)


class PartialExtractionError(RuntimeError):
    """Raised when an extraction finished with gaps and must not be persisted."""


def assert_extraction_complete(failures: dict[str, str], entity_name: str) -> None:
    """Raises if any status failed, so the incomplete snapshot is never written.
    
    A 406 is not failure and must not reach this function: the API answers it
    with an empty result set, which is legitimate outcome.
    """
    if not failures:
        return

    detail = "; ".join(f"{status}: {error}" for status, error in sorted(failures.items()))
    logger.error(f"{entity_name}:{len(failures)} status(es) failed, refusing to write the snapshot.")
    raise PartialExtractionError(
        f"{len(failures)} status(es) failed during '{entity_name}' extraction, so the "
        f"snapshot is incomplete and will not be saved. Failures -> {detail}"
    )