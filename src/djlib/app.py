import asyncio
import tempfile
from pathlib import Path
from types import TracebackType
from typing import List, Optional, Self, Type

from .database import Database
from .libraries import Library, RekordboxLibrary, SpotifyLibrary
from .logging import logger
from .models import Track


class App:
    def __init__(self):
        self._libraries = {"spotify": SpotifyLibrary(), "rekordbox": RekordboxLibrary()}

    @property
    def spotify(self) -> SpotifyLibrary:
        return self._libraries["spotify"]

    @property
    def rekordbox(self) -> RekordboxLibrary:
        return self._libraries["rekordbox"]

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

        for library in self._libraries.values():
            await library.connect()

    async def close(self) -> None:
        await self._database.close()
        for library in self._libraries.values():
            await library.close()

    async def refresh(self) -> None:
        """Refresh all libraries."""
        await asyncio.gather(*(library.refresh() for library in self._libraries))

    async def update(self, source: type[Library], target: type[Library]) -> None:
        """Update tracks and playlists TARGET to match SOURCE."""
        logger.info(f"Updating {source} to match {target}")
        missing_tracks = await self._get_missing_tracks(source, target)
        if missing_tracks:
            with tempfile.TemporaryDirectory() as export_directory:
                exported_track_paths = await self._export_missing_tracks(
                    missing_tracks, source, export_directory
                )
                asyncio.gather(
                    *(
                        target.import_track(track_path)
                        for track_path in exported_track_paths
                    )
                )

        # TODO: Update local playlists
        # TODO: Update client playlists

        logger.info(f"Finished updating {source} to match {target}")

    async def _get_missing_tracks(
        self, source: type[Library], target: type[Library]
    ) -> List[type[Track]]:
        """Return a QuerySet of tracks from synced playlists not found in TARGET."""
        logger.debug(f"Getting tracks in {source} not in {target}")
        target_isrcs = (
            await target.tracks.all()
            .exclude(isrc=None)
            .order_by("isrc")
            .distinct()
            .values_list("isrc", flat=True)
        )
        return (
            await source.tracks.in_synced_playlists()
            .exclude(isrc=None)
            .exclude(isrc__in=target_isrcs)
        )

    async def _export_missing_tracks(
        self,
        missing_tracks: List[type[Track]],
        source: type[Library],
        export_directory: Path,
    ) -> None:
        logger.info(f"Exporting {len(missing_tracks)} from {source}")
        exported_track_paths = await asyncio.gather(
            *(source.export_track(track, export_directory) for track in missing_tracks),
            return_exceptions=True,
        )
        result = []
        for i, path in enumerate(exported_track_paths):
            if isinstance(path, Exception):
                logger.error(f"Failed to export {missing_tracks[i]}: {path}")
            else:
                result.append(path)

        return result
