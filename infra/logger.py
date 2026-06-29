import logging
import os
from logging.handlers import TimedRotatingFileHandler

LOG_RETENTION_DAYS = 30

def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger that writes to console and to a daily-rotating log file."""

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

    # file handler: rotates at midnight, keeps only the last LOG_RETENTION_DAYS files
    os.makedirs("logs", exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        os.path.join("logs", "pipeline.log"),
        when="midnight",
        backupCount=LOG_RETENTION_DAYS,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger