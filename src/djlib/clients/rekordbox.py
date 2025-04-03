import asyncio
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import List, AsyncGenerator

from pyrekordbox import Rekordbox6Database
from pyrekordbox.db6.tables import DjmdContent, DjmdSongPlaylist, PlaylistType
from sqlalchemy import asc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload

from ..logging import logger
from ..models import RekordboxPlaylist, RekordboxTrack
from .abstract import Client


class RekordboxClient(Client):
    """Class for interfacing with a rekordbox library."""

    _rekordbox_database_semaphore = asyncio.Semaphore()

    async def connect(self) -> None:
        logger.debug(f"Starting {self}")
        # TODO: Download rekordbox db key
        self._rekordbox_database = await asyncio.to_thread(Rekordbox6Database)

    async def close(self) -> None:
        logger.debug(f"Closing {self}")
        await asyncio.to_thread(self._rekordbox_database.close)

    async def get_playlists(self) -> AsyncGenerator[RekordboxPlaylist, None]:
        db_playlists = await asyncio.to_thread(
            self._rekordbox_database.get_playlist,
            Attribute=PlaylistType.PLAYLIST,  # Exclude folders and smart playlists
        )
        for db_playlist in db_playlists:
            yield RekordboxPlaylist(external_id=db_playlist.ID, name=db_playlist.Name)

    async def get_playlist_tracks(
        self, playlist: RekordboxPlaylist
    ) -> AsyncGenerator[RekordboxTrack, None]:
        # TODO: Read ISRC tags concurrently
        db_tracks = await asyncio.to_thread(self._get_playlist_contents, playlist)
        for db_track in db_tracks:
            yield await RekordboxTrack.from_rb(db_track)

    def _get_playlist_contents(self, playlist: RekordboxPlaylist) -> List[DjmdContent]:
        logger.debug(f"Getting playlist contents for {playlist}")
        song_playlist_objects = (
            self._rekordbox_database.query(DjmdSongPlaylist)
            .options(joinedload(DjmdSongPlaylist.Content))
            .filter(DjmdSongPlaylist.PlaylistID == playlist.external_id)
            .order_by(asc(DjmdSongPlaylist.TrackNo))
            .all()
        )
        return [song_playlist.Content for song_playlist in song_playlist_objects]

    async def export_track(
        self, track: type[RekordboxTrack], export_directory: Path
    ) -> Path:
        logger.debug(f"Exporting {track} to {export_directory}")
        await asyncio.to_thread(
            shutil.copy,
            track.path,
            export_directory / f"{track.isrc}{track.path.suffix}",
        )

    async def import_track(self, track: RekordboxTrack) -> None:
        logger.debug(f"Importing {track}")
        non_unique_import_path = track.import_path()
        if non_unique_import_path.exists():
            logger.warning(f"Track already exists at {non_unique_import_path}")

        import_path = track.import_path(unique=True)
        logger.debug(f"Moving {track.path} to {import_path}")
        import_path.parent.mkdir(parents=True, exist_ok=True)
        track.path.rename(import_path)
        track.path = import_path

        async with self._rekordbox_database_semaphore:
            # TODO: Make async
            db_track = self._rekordbox_database.add_content(
                track.path, Title=track.title
            )
            self._rekordbox_database.commit()

        track.external_id = db_track.ID

    async def update_playlist(self, playlist: RekordboxPlaylist) -> None:
        """Update PLAYLIST in rekordbox."""
        # TODO: Make async
        async with self._rekordbox_database_semaphore:
            logger.debug(f"Updating {playlist}")
            try:
                db_playlist = self._rekordbox_database.get_playlist(
                    Name=playlist.name, Attribute=PlaylistType.PLAYLIST
                ).one()
            except NoResultFound:
                db_playlist = self._rekordbox_database.create_playlist(playlist.name)
                logger.debug(f"Created playlist on rekordbox: {playlist.name}")
                self._rekordbox_database.commit()

            db_songs = sorted(db_playlist.Songs, key=lambda s: s.TrackNo)
            db_song_ids = [int(s.Content.ID) for s in db_songs]
            local_song_ids = await playlist.tracks.values_list("external_id", flat=True)
            local_song_ids = list(local_song_ids)
            if db_song_ids != local_song_ids:
                for song in db_playlist.Songs:
                    self._rekordbox_database.remove_from_playlist(db_playlist, song)

                async for track in playlist.tracks.all():
                    db_track = self._rekordbox_database.get_content(
                        ID=track.external_id
                    )
                    self._rekordbox_database.add_to_playlist(db_playlist, db_track)

                self._rekordbox_database.commit()

    async def get_non_playlist_tracks(self) -> AsyncGenerator[RekordboxTrack, None]:
        non_playlist_tracks = (
            self._rekordbox_database.query(DjmdContent)
            .outerjoin(DjmdSongPlaylist, DjmdContent.ID == DjmdSongPlaylist.ContentID)
            .filter(DjmdSongPlaylist.ID.is_(None))
            .all()
        )
        for db_track in non_playlist_tracks:
            yield await RekordboxTrack.from_rb(db_track)
