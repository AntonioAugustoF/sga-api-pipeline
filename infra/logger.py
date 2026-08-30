import glob
import logging
import os
import sys
import time
from datetime import date

LOG_RETENTION_DAYS = 30
LOG_DIR = "logs"


def _prune_old_logs(log_dir: str) -> None:
    """Deletes daily log files older than LOG_RETENTION_DAYS."""
    cutoff = time.time() - LOG_RETENTION_DAYS * 86400
    for path in glob.glob(os.path.join(log_dir, "pipeline_*.log")):
        if os.path.getmtime(path) < cutoff:
            os.remove(path)


def _running_under_pytest() -> bool:
    """True when the process was started by pytest.
    
    Detected via sys.modules rather than PYTEST_CURRENT_TEST because most
    get_logger calls happen at import time, during collection, when that
    environment variable has not been set yet.
    """
    return "pytest" in sys.modules


def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger that writes to console and to a daily log file.

    Uses one file per calendar day (append-only, never renamed) instead of an
    in-place rotating file: Prefect runs each flow in its own subprocess, and
    Windows refuses to rename a log file another process still has open —
    which TimedRotatingFileHandler's rollover-via-rename hit on every write.
    """

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # The suite exercises failure paths on purpose, so its ERROR lines used to land
    # in the same daily file used to diagnose real incidents. Ruling out fabricated
    # errors already cost time twice while investigating a run that had none.
    # Returning early also keeps _prune_old_logs from deleting production logs
    # merely because a module was imported by a test.
    if _running_under_pytest():
        return logger

    # File handler: one file per day, opened in append mode. Multiple processes
    # can safely append to the same file concurrently — only rename/rollover
    # requires exclusive access on Windows.
    os.makedirs(LOG_DIR, exist_ok=True)
    _prune_old_logs(LOG_DIR)
    log_path = os.path.join(LOG_DIR, f"pipeline_{date.today():%Y-%m-%d}.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
