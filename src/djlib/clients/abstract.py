from abc import ABC, abstractmethod
from collections.abc import Generator
from types import TracebackType
from typing import Optional, Self, Type

from ..models import Playlist, Track


class Client(ABC):
    """Class for interfacing with an external music library."""

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[type[BaseException]],
        exc_tb: Optional[TracebackType],
    ):
        await self.close()

    @abstractmethod
    async def connect(self) -> None:
        """Open connection to external library."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to external library."""
        pass

    @abstractmethod
    async def get_playlists(self) -> Generator[type[Playlist]]:
        pass

    @abstractmethod
    async def get_playlist_tracks(
        self, playlist: type[Playlist]
    ) -> Generator[type[Track]]:
        pass
