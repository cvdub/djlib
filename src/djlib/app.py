import asyncio
import tempfile
import time
from pathlib import Path
from types import TracebackType
from typing import Optional, Self, Type

from .clients import TrackExportError
from .database import Database
from .libraries import Library, RekordboxLibrary, SpotifyLibrary
from .logging import logger
from .models import PlaylistStatus


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
        await asyncio.gather(
            *(library.refresh() for library in self._libraries.values())
        )

    async def update(self, source: type[Library], target: type[Library]) -> None:
        """Update tracks and playlists TARGET to match SOURCE."""
        start_time = time.perf_counter()
        logger.info(f"Updating {source} to match {target}")

        logger.debug(f"Getting tracks in {source} not in {target}")
        missing_tracks = await source.tracks_not_in(target)
        if missing_tracks:
            logger.info(f"Exporting {len(missing_tracks)} tracks from {source}")

        with tempfile.TemporaryDirectory() as export_directory:
            export_directory = Path(export_directory)
            export_track_tasks = []
            for track in missing_tracks:
                task = source.export_track(track, export_directory)
                export_track_tasks.append(task)

            async with asyncio.TaskGroup() as tg:
                num_exported = 0
                for task in asyncio.as_completed(export_track_tasks):
                    result = await task
                    if isinstance(result, TrackExportError):
                        logger.warning(f"{result}")
                    else:
                        num_exported += 1
                        tg.create_task(target.import_track(result))

        logger.info(f"Imported {num_exported:,} tracks to {target}")

        source_playlists = await source.playlists.filter(status=PlaylistStatus.SYNCED)
        async with asyncio.TaskGroup() as tg:
            for source_playlist in source_playlists:
                tg.create_task(target.update_playlist_to_match_source(source_playlist))

        end_time = time.perf_counter()
        time_elapsed = end_time - start_time
        logger.info(
            f"Finished updating {source} to match {target} (completed in "
            f"{time_elapsed:,.2f} seconds)"
        )
