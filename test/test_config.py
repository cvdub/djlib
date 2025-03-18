from djlib.config import Config


def test_mocked_cache_directory():
    assert "djlib-test" in Config.cache_directory
