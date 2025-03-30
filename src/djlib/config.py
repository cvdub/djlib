import logging
from pathlib import Path

from platformdirs import user_cache_dir


class Config:
    cache_directory: Path = user_cache_dir("djlib", ensure_exists=True)
    log_level: int = logging.DEBUG
    database_file: str = "db.sqlite3"
