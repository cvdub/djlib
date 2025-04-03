import logging
from contextlib import contextmanager

from pydub import AudioSegment

from .config import Config

Disable deprecation warnings
logging.captureWarnings(True)

# Suppress pydub console messages
# logging.getLogger("pydub").setLevel(logging.CRITICAL)

# Configure djlib logger
logger = logging.getLogger("djlib")
logger.setLevel(Config.log_level)
handler = logging.StreamHandler()
handler.setLevel(Config.log_level)
log_format = "{asctime} {levelname:>7}: {message}"
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
