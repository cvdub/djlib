import logging
from unittest.mock import patch

import pytest
from djlib.config import Config
from djlib.logging import override_log_level
from platformdirs import user_cache_dir


@pytest.fixture(scope="session", autouse=True)
def config():
    with patch.object(
        Config,
        "cache_directory",
        new=user_cache_dir("djlib-test", ensure_exists=True),
    ):
        yield


@pytest.fixture(scope="session", autouse=True)
def set_log_level_to_debug():
    with override_log_level(logging.DEBUG):
        yield
