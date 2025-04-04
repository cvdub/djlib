import asyncio
import contextlib
import shutil
import threading
from pathlib import Path
from typing import AsyncGenerator, List

from pyrekordbox import Rekordbox6Database
from pyrekordbox.db6.tables import (
    DjmdAlbum,
    DjmdContent,
    DjmdSongPlaylist,
    PlaylistType,
)
from sqlalchemy import asc
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import joinedload, selectinload

from ..logging import logger
from ..models import RekordboxPlaylist, RekordboxTrack
from .abstract import Client


class RekordboxClient(Client):
    """Class for interfacing with a rekordbox library."""

    # TODO: Make Rekordbox6Database async

    _rekordbox_database_semaphore = threading.Semaphore()

    def _open_db(self) -> contextlib.AbstractContextManager[Rekordbox6Database]:
        @contextlib.contextmanager
        def _context_manager():
            with self._rekordbox_database_semaphore, self._rekordbox_database:
                self._rekordbox_database.open()
                yield self._rekordbox_database

        return _context_manager()

    async def connect(self) -> None:
        logger.debug(f"Starting {self}")
        # TODO: Download rekordbox db key
        self._rekordbox_database = await asyncio.to_thread(Rekordbox6Database)

    async def close(self) -> None:
        logger.debug(f"Closing {self}")
        if self._rekordbox_database.session:
            self._rekordbox_database.close()

    async def get_playlists(self) -> AsyncGenerator[RekordboxPlaylist, None]:
        playlists = await asyncio.to_thread(self._get_playlists)
        for playlist in playlists:
            yield playlist

    def _get_playlists(self) -> List[RekordboxPlaylist]:
        results = []
        with self._open_db():
            # Exclude folders and smart playlists
            for db_playlist in self._rekordbox_database.get_playlist(
                Attribute=PlaylistType.PLAYLIST
            ):
                results.append(
                    RekordboxPlaylist(external_id=db_playlist.ID, name=db_playlist.Name)
                )

        return results

    async def get_playlist_tracks(
        self, playlist: RekordboxPlaylist
    ) -> AsyncGenerator[RekordboxTrack, None]:
        # TODO: Read ISRC tags concurrently
        db_tracks = await asyncio.to_thread(self._get_playlist_contents, playlist)
        for db_track in db_tracks:
            yield await RekordboxTrack.from_rb(db_track)

    def _get_playlist_contents(self, playlist: RekordboxPlaylist) -> List[DjmdContent]:
        with self._open_db():
            logger.debug(f"Getting playlist contents for {playlist}")
            song_playlist_objects = (
                self._rekordbox_database.query(DjmdSongPlaylist)
                .options(
                    joinedload(DjmdSongPlaylist.Content).joinedload(DjmdContent.Artist),
                    joinedload(DjmdSongPlaylist.Content)
                    .joinedload(DjmdContent.Album)
                    .selectinload(DjmdAlbum.AlbumArtist),
                )
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
        await asyncio.to_thread(import_path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(track.path.rename, import_path)
        track.path = import_path
        db_track = await asyncio.to_thread(self._save_track, track)
        track.external_id = db_track.ID

    def _save_track(self, track: RekordboxTrack) -> DjmdContent:
        with self._open_db():
            db_track = self._rekordbox_database.add_content(
                track.path, Title=track.title
            )
            self._rekordbox_database.commit()
            return db_track

    async def update_playlist(self, playlist: RekordboxPlaylist) -> None:
        """Update PLAYLIST in rekordbox."""
        logger.debug(f"Updating {playlist}")
        local_song_ids = await playlist.tracks.values_list("external_id", flat=True)
        local_song_ids = list(local_song_ids)
        playlist_tracks = await playlist.tracks.all()
        await asyncio._to_thread(
            self._update_playlist, playlist, local_song_ids, playlist_tracks
        )

    def _update_playlist(self, playlist, local_song_ids, playlist_tracks) -> None:
        with self._open_db():
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

            if db_song_ids != local_song_ids:
                for song in db_playlist.Songs:
                    self._rekordbox_database.remove_from_playlist(db_playlist, song)

                for track in playlist_tracks:
                    db_track = self._rekordbox_database.get_content(
                        ID=track.external_id
                    )
                    self._rekordbox_database.add_to_playlist(db_playlist, db_track)

                self._rekordbox_database.commit()

    async def get_non_playlist_tracks(self) -> AsyncGenerator[RekordboxTrack, None]:
        non_playlist_tracks = await asyncio.to_thread(self._get_non_playlist_tracks)
        for db_track in non_playlist_tracks:
            yield await RekordboxTrack.from_rb(db_track)

    def _get_non_playlist_tracks(self) -> List[RekordboxTrack]:
        with self._open_db():
            # Query DjmdContent and eagerly load Artist, Album, and AlbumArtist
            # to prevent DetachedInstanceError when accessing relations later
            query = (
                self._rekordbox_database.query(DjmdContent)
                .options(
                    selectinload(DjmdContent.Artist),
                    selectinload(DjmdContent.Album).selectinload(DjmdAlbum.AlbumArtist),
                )
                .outerjoin(
                    DjmdSongPlaylist, DjmdContent.ID == DjmdSongPlaylist.ContentID
                )
                .filter(DjmdSongPlaylist.ID.is_(None))
            )
            return query.all()
