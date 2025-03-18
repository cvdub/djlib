from unittest.mock import patch

import pytest
from djlib.config import Config
from platformdirs import user_cache_dir


@pytest.fixture(scope="session", autouse=True)
def config():
    with patch.object(
        Config, "cache_directory", new=user_cache_dir("djlib-test", ensure_exists=True)
    ):
        yield
