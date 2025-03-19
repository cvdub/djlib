import asyncio
from collections.abc import Generator
from pathlib import Path
from types import TracebackType
from typing import Optional, Self, Type

from pyrekordbox import Rekordbox6Database

from ..models import RekordboxPlaylist, RekordboxTrack
from .abstract import Client


class RekordboxClient(Client):
    """Class for interfacing with a Spotify library."""

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

    async def connect(self):
        # TODO: Download rekordbox db key
        self._rekordbox_database = await asyncio.to_thread(Rekordbox6Database)

    async def close(self) -> None:
        await asyncio.to_thread(self._rekordbox_database.close)

    async def get_playlists(self) -> Generator[RekordboxPlaylist]:
        # TODO: Order playlists
        # TODO: Join artist and album
        db_playlists = await asyncio.to_thread(self._rekordbox_database.get_playlist)
        for db_playlist in db_playlists:
            yield RekordboxPlaylist(external_id=db_playlist.ID, name=db_playlist.Name)

    async def get_playlist_tracks(self, playlist) -> Generator[RekordboxTrack]:
        db_tracks = await asyncio.to_thread(
            self._rekordbox_database.get_playlist_contents, playlist.external_id
        )
        for db_track in db_tracks:
            yield RekordboxTrack(
                external_id=db_track.ID,
                title=db_track.Title,
                artist=db_track.Artist.Name,
                album=db_track.Album.Name,
                track_number=db_track.TrackNo,
                disc_number=db_track.DiscNo,
                path=Path(db_track.FolderPath),
                # TODO: album_artist
                # TODO: ISRC
            )
