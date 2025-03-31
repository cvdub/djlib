from types import TracebackType
from typing import Optional, Self, Type

from tortoise import Tortoise

from .config import Config
from .logging import logger


class Database:
    def __str__(self) -> str:
        return f"<{self.__class__.__name__}>"

    async def start(self) -> None:
        logger.debug(f"Starting {self}")
        await Tortoise.init(
            db_url=f"sqlite://{Config.database_file}",
            modules={"models": ["djlib.models"]},
        )
        await Tortoise.generate_schemas()

    async def close(self) -> None:
        logger.debug(f"Closing {self}")
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
