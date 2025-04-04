from abc import ABC, abstractmethod
from pathlib import Path
from types import TracebackType
from typing import AsyncGenerator, Optional, Self, Type

from ..models import Playlist, Track


class TrackExportError(Exception):
    pass


class Client(ABC):
    """Class for interfacing with an external music library."""

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}>"

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
    async def get_playlists(self) -> AsyncGenerator[type[Playlist], None]:
        pass

    @abstractmethod
    async def get_playlist_tracks(
        self, playlist: type[Playlist]
    ) -> AsyncGenerator[type[Track], None]:
        pass

    @abstractmethod
    async def export_track(self, track: type[Track], export_directory: Path) -> Path:
        """Export TRACK from external library, saving it in EXPORT_DIRECTORY.

        Returns a path to the exported track.
        """
        pass

    @abstractmethod
    async def import_track(self, track_path: Path) -> type[Track]:
        """Import track at TRACK_PATH to external library."""
        pass

    @abstractmethod
    async def update_playlist(self, playlist: type[Playlist]) -> None:
        """Update PLAYLIST on external library."""
        pass
