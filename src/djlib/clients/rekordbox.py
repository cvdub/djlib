import asyncio
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import List, Optional

from mutagen import MutagenError
from mutagen.id3 import ID3
from pyrekordbox import Rekordbox6Database
from pyrekordbox.db6.tables import DjmdContent, DjmdSongPlaylist, PlaylistType
from sqlalchemy import asc
from sqlalchemy.orm import joinedload

from ..logging import logger
from ..models import RekordboxPlaylist, RekordboxTrack
from .abstract import Client


class RekordboxClient(Client):
    """Class for interfacing with a rekordbox library."""

    async def connect(self) -> None:
        # TODO: Download rekordbox db key
        self._rekordbox_database = await asyncio.to_thread(Rekordbox6Database)

    async def close(self) -> None:
        await asyncio.to_thread(self._rekordbox_database.close)

    async def get_playlists(self) -> Generator[RekordboxPlaylist]:
        db_playlists = await asyncio.to_thread(
            self._rekordbox_database.get_playlist,
            Attribute=PlaylistType.PLAYLIST,  # Exclude folders and smart playlists
        )
        for db_playlist in db_playlists:
            yield RekordboxPlaylist(external_id=db_playlist.ID, name=db_playlist.Name)

    async def get_playlist_tracks(
        self, playlist: RekordboxPlaylist
    ) -> Generator[RekordboxTrack]:
        # TODO: Read ISRC tags concurrently
        db_tracks = await asyncio.to_thread(self._get_playlist_contents, playlist)
        for db_track in db_tracks:
            # ISRC isn't stored properly by rekordbox,
            # so it must be pulled from the ID3 tag
            # TODO: Pull isrc tags concurrently
            isrc = await asyncio.to_thread(self._read_isrc_tag, db_track.FolderPath)
            try:
                track_number = int(db_track.TrackNo)
            except TypeError:
                track_number = 1

            if track_number < 1:
                logger.warning(
                    f"Invalid track number: {track_number} on "
                    f"RekordboxTrack {db_track.FolderPath}"
                )
                track_number = None

            try:
                disc_number = int(db_track.DiscNo)
            except TypeError:
                disc_number = 1

            if disc_number < 0:
                disc_number = 0

            yield RekordboxTrack(
                external_id=db_track.ID,
                title=db_track.Title,
                artist=getattr(db_track.Artist, "Name", None),
                album=getattr(db_track.Album, "Name", None),
                album_artist=getattr(db_track.AlbumArtist, "Name", None),
                track_number=track_number,
                disc_number=disc_number,
                path=Path(db_track.FolderPath),
                isrc=isrc,
            )

    def _get_playlist_contents(self, playlist: RekordboxPlaylist) -> List[DjmdContent]:
        logger.debug(f"Getting rekordbox playlist contents for {playlist.name}")
        song_playlist_objects = (
            self._rekordbox_database.query(DjmdSongPlaylist)
            .options(joinedload(DjmdSongPlaylist.Content))
            .filter(DjmdSongPlaylist.PlaylistID == playlist.external_id)
            .order_by(asc(DjmdSongPlaylist.TrackNo))
            .all()
        )
        return [song_playlist.Content for song_playlist in song_playlist_objects]

    def _read_isrc_tag(self, track_path: Path) -> Optional[str]:
        try:
            audio = ID3(track_path)
        except MutagenError:
            logger.warning(f"Failed to read ISRC tag from {track_path}")
            return None

        isrc = str(audio.get("TSRC", "")) or None
        if isrc:
            isrc = isrc.replace("-", "")

        return isrc

    async def export_track(
        self, track: type[RekordboxTrack], export_directory: Path
    ) -> Path:
        logger.info(f"Exporting {track} to {export_directory}")
        await asyncio.to_thread(
            shutil.copy,
            track.path,
            export_directory / f"{track.isrc}{track.path.suffix}",
        )
