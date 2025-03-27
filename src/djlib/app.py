import asyncio
from types import TracebackType
from typing import Optional, Self, Type

from .database import Database
from .libraries import RekordboxLibrary, SpotifyLibrary


class App:
    _library_classes = [SpotifyLibrary, RekordboxLibrary]

    def __init__(self):
        self._libraries = []

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

    async def start(self) -> None:
        self._database = Database()
        await self._database.start()

        for library_class in self._library_classes:
            library = library_class()
            await library.connect()
            self._libraries.append(library)

    async def close(self) -> None:
        for library in self._libraries:
            await library.close()

    async def refresh(self) -> None:
        """Refresh all libraries."""
        await asyncio.gather(*(library.refresh() for library in self._libraries))
