from abc import ABC, abstractmethod
from collections.abc import Generator

from ..models import Playlist, Track


class Client(ABC):
    """Class for interfacing with an external music library."""

    @abstractmethod
    async def get_playlists(self) -> Generator[type[Playlist]]:
        pass

    @abstractmethod
    async def get_playlist_tracks(
        self, playlist: type[Playlist]
    ) -> Generator[type[Track]]:
        pass
