import logging
import os
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger that writes to console and to a daily log file."""

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # file handler
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join("logs", f"pipeline_{current_date}.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger