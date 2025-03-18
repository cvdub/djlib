from types import TracebackType
from typing import Optional, Self, Type

from tortoise import Tortoise

from .config import Config
from .logging import logger


class Database:
    async def start(self) -> None:
        logger.debug("Starting database")
        await Tortoise.init(
            db_url=f"sqlite://{Config.database_file}",
            modules={"models": ["djlib.models"]},
        )
        await Tortoise.generate_schemas()

    async def close(self) -> None:
        logger.debug("Closing database")
        await Tortoise.close_connections()

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[type[BaseException]],
        exc_tb: Optional[TracebackType],
    ):
        await self.close()
