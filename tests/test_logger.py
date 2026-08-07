import logging

from infra.logger import _running_under_pytest, get_logger


def test_that_detects_that_it_is_running_under_pytest():
    assert _running_under_pytest()


def test_no_file_handler_is_attached_under_pytest():
    """Fabricated errors from the suite must never reach the daily production log."""
    logger = get_logger("test_logger_isolation")

    assert [h for h in logger.handlers if isinstance(h, logging.FileHandler)] == []


def test_console_handler_is_still_attached():
    logger = get_logger("test_logger_console")

    # FileHandler subclasses StreamHandler, so excluding it is what makes this
    # assertion mean "console" rather than "any handler at all".
    assert any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in logger.handlers
    )