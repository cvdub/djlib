import asyncio
from abc import ABC
from types import TracebackType
from typing import Optional, Self, Type

from tortoise.exceptions import IntegrityError

from ..clients import Client
from ..logging import logger
from ..models import Playlist, Track


class Library(ABC):
    """Class for managing a music library."""

    client_class: Type[Client] = None
    playlists: Type[Playlist] = None
    tracks: Type[Track] = None

    def __init__(self):
        if self.client_class is None:
            raise AttributeError(
                '"client_class" must be defined on subclasses of Library.'
            )

        if self.playlists is None:
            raise AttributeError(
                '"playlists" must be defined on subclasses of Library.'
            )

        if self.tracks is None:
            raise AttributeError(
                '"playlists" must be defined on subclasses of Library.'
            )

        self._client = self.client_class()

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

    async def connect(self) -> None:
        """Open client connection."""
        await self._client.connect()

    async def close(self) -> None:
        """Close client connection."""
        await self._client.close()

    async def refresh(self) -> None:
        """Refresh local models with external data from client."""
        logger.info(f"Refreshing {self.__class__.__name__}")

        # Cache updated tracks to avoid calling create/update
        # multiple times on the same track
        self._tracks_external_id_map = {}

        client_playlists = []
        async with asyncio.TaskGroup() as tg:
            async for client_playlist in self._client.get_playlists():
                client_playlists.append(client_playlist)
                tg.create_task(self._refresh_playlist(client_playlist))

            tg.create_task(self._refresh_non_playlist_tracks())

        # Delete local playlists that no longer exist on client
        await self.playlists.exclude(
            external_id__in=(
                client_playlist.external_id for client_playlist in client_playlists
            )
        ).delete()

        logger.info(f"Finished refreshing {self.__class__.__name__}")

    async def _refresh_playlist(self, client_playlist: type[Playlist]) -> None:
        logger.debug(f"Refreshing {self.playlists.__name__} {client_playlist.name}")
        try:
            local_playlist, created = await self.playlists.update_or_create(
                external_id=client_playlist.external_id,
                defaults={"name": client_playlist.name},
            )
        except IntegrityError:
            logger.error(
                f"Ignoring duplicate {self.playlists.__name__} with "
                f"name {client_playlist.name}"
            )
        else:
            if local_playlist.differs_from(client_playlist):
                await self._refresh_playlist_tracks(local_playlist)
                await local_playlist.update_to_match(client_playlist)

            logger.debug(
                f"Finished refreshing {self.playlists.__name__} {client_playlist.name}"
            )

    async def _refresh_playlist_tracks(self, playlist: type[Playlist]) -> None:
        tracks = []
        async with asyncio.TaskGroup() as tg:
            async for track in self._client.get_playlist_tracks(playlist):
                try:
                    tracks.append(self._tracks_external_id_map[track.external_id])
                except KeyError:
                    tg.create_task(track.set_id_and_save())
                    self._tracks_external_id_map[track.external_id] = track
                    tracks.append(track)

        await playlist.add_tracks(*tracks, delete_existing=True)

    async def _refresh_non_playlist_tracks(self) -> None:
        pass
