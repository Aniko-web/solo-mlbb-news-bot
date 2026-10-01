import logging
import sys
from typing import Optional


def setup_logger(name: str = "mlbb_agent", log_level: Optional[str] = None) -> logging.Logger:
    """
    Configure and return a structured logger with console output.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, (log_level or "INFO").upper(), logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logger()
