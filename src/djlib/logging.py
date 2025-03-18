import logging
from contextlib import contextmanager

from .config import Config

logger = logging.getLogger("djlib")
logger.setLevel(Config.log_level)
handler = logging.StreamHandler()
handler.setLevel(Config.log_level)
log_format = "{asctime} {levelname:>5}: {message}"
formatter = logging.Formatter(log_format, style="{")
handler.setFormatter(formatter)
logger.addHandler(handler)


@contextmanager
def override_log_level(level):
    original_level = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(original_level)
