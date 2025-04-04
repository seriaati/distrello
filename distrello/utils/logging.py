from __future__ import annotations

import inspect
import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_dir: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=logging.INFO)
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    logger.add(log_dir, rotation="1 day", retention="7 days", level=logging.DEBUG)
