import asyncio
from abc import ABC
from pathlib import Path
from types import TracebackType
from typing import List, Optional, Self, Type, Union

from tortoise.exceptions import IntegrityError

from ..clients import Client, TrackExportError
from ..logging import logger
from ..models import Playlist, PlaylistStatus, Track


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

    async def connect(self) -> None:
        """Open client connection."""
        await self._client.connect()

    async def close(self) -> None:
        """Close client connection."""
        await self._client.close()

    async def refresh(self) -> None:
        """Refresh local models with external data from client."""
        logger.info(f"Refreshing {self}")

        # Cache updated tracks to avoid calling create/update
        # multiple times on the same track
        self._tracks_external_id_map = {}

        client_playlists = []
        async with asyncio.TaskGroup() as tg:
            async for client_playlist in self._client.get_playlists():
                client_playlists.append(client_playlist)
                tg.create_task(self._refresh_playlist(client_playlist))

        # Delete local playlists that no longer exist on client
        await self.playlists.exclude(
            external_id__in=(
                client_playlist.external_id for client_playlist in client_playlists
            )
        ).delete()

        await self._refresh_non_playlist_tracks()

        logger.info(f"Finished refreshing {self}")

    async def _refresh_playlist(self, client_playlist: type[Playlist]) -> None:
        logger.debug(f"Refreshing {client_playlist}")
        try:
            local_playlist, created = await self.playlists.update_or_create(
                external_id=client_playlist.external_id,
                defaults={"name": client_playlist.name},
            )
        except IntegrityError:
            logger.error(f"Ignoring duplicate {client_playlist}")
        else:
            if local_playlist.differs_from(client_playlist):
                await self._refresh_playlist_tracks(local_playlist)
                await local_playlist.update_to_match(client_playlist)

            logger.debug(f"Finished refreshing {client_playlist}")

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

    async def export_track(
        self, track: type[Track], export_directory: Path
    ) -> Union[Path, TrackExportError]:
        try:
            return await self._client.export_track(track, export_directory)
        except TrackExportError as e:
            return e

    async def import_track(self, track_path: Path) -> type[Track]:
        track = await asyncio.to_thread(self.tracks.from_file, track_path)
        await self._client.import_track(track)
        await track.save()
        logger.debug(f"Imported {track}")

    async def update_playlist_to_match_source(
        self, source_playlist: type[Playlist]
    ) -> None:
        playlist, created = await self.playlists.update_or_create(
            name=source_playlist.name, defaults={"status": PlaylistStatus.SYNCED}
        )

        if created:
            logger.debug(f"Created {playlist}")

        # Get all source track ISRCs at once
        source_isrcs = await source_playlist.tracks.exclude(isrc=None).values_list(
            "isrc", flat=True
        )
        source_isrcs = list(source_isrcs)  # Convert to list for comparison

        # Get current playlist track ISRCs
        current_isrcs = await playlist.tracks.exclude(isrc=None).values_list(
            "isrc", flat=True
        )
        current_isrcs = list(current_isrcs)  # Convert to list for comparison

        # Only update if the tracks differ (by ISRC and order)
        if current_isrcs != source_isrcs:
            logger.debug(
                f"Updating {playlist} to match {source_playlist} - tracks differ"
            )

            # Find all matching tracks in a single query
            matching_tracks = await self.tracks.filter(isrc__in=source_isrcs)

            # Create a lookup map for faster access
            tracks_by_isrc = {track.isrc: track for track in matching_tracks}

            # Build the final tracks list in the same order as source tracks
            tracks = []
            for isrc in source_isrcs:
                if track := tracks_by_isrc.get(isrc):
                    tracks.append(track)
                else:
                    logger.warning(f"Missing track for {playlist} with ISRC: {isrc}")

            await playlist.add_tracks(*tracks, delete_existing=True)
            await self._client.update_playlist(playlist)
        else:
            logger.debug(
                f"No update needed for {playlist} - tracks match {source_playlist}"
            )

    async def tracks_not_in(self, target: type[Self]) -> List[type[Track]]:
        """Return a QuerySet of tracks from synced playlists not found in OTHER."""
        target_isrcs = (
            await target.tracks.all().exclude(isrc=None).values_list("isrc", flat=True)
        )
        return (
            await self.tracks.in_synced_playlists()
            .exclude(isrc=None)
            .exclude(isrc__in=target_isrcs)
        )
