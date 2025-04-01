import asyncio
from pathlib import Path
from typing import Optional, Self

from mutagen import MutagenError
from mutagen.id3 import ID3
from pyrekordbox.db6.tables import DjmdContent
from tortoise import fields

from ..config import Config
from ..logging import logger
from .abstract import Playlist, PlaylistTrack, Track


class RekordboxPlaylist(Playlist):
    external_id = fields.CharField(max_length=255, unique=True)
    playlist_tracks: fields.ReverseRelation["RekordboxPlaylistTrack"]


class RekordboxTrack(Track):
    external_id = fields.CharField(max_length=255, unique=True)
    path = fields.CharField(max_length=255, unique=True)

    @classmethod
    async def from_rb(cls, db_track: DjmdContent) -> Self:
        # ISRC isn't stored properly by rekordbox,
        # so it must be pulled from the ID3 tag
        # TODO: Pull isrc tags concurrently
        isrc = await asyncio.to_thread(cls._read_isrc_tag, db_track.FolderPath)
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

        return cls(
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

    @classmethod
    def _read_isrc_tag(cls, track_path: Path) -> Optional[str]:
        try:
            audio = ID3(track_path)
        except MutagenError:
            logger.warning(f"Failed to read ISRC tag from {track_path}")
            return None

        isrc = str(audio.get("TSRC", "")) or None
        if isrc:
            isrc = isrc.replace("-", "")

        return isrc

    @classmethod
    def from_file(cls, track_path: Path) -> Self:
        track = super().from_file(track_path)
        track.path = track_path
        return track

    def import_path(self, unique=False) -> Path:
        import_path = (
            Config.music_directory
            / str(self.artist)
            / str(self.album)
            / f"{self.track_number or 1:02} {self.title}{self.path.suffix}"
        )
        if not unique:
            return import_path

        duplicate_num = 1
        unique_import_path = import_path
        while unique_import_path.exists():
            unique_import_path = import_path.with_stem(
                f"{import_path.stem} ({duplicate_num})"
            )
            duplicate_num += 1

        return unique_import_path


class RekordboxPlaylistTrack(PlaylistTrack):
    playlist: fields.ForeignKeyRelation[RekordboxPlaylist] = fields.ForeignKeyField(
        "models.RekordboxPlaylist", related_name="playlist_tracks"
    )
    track: fields.ForeignKeyRelation[RekordboxTrack] = fields.ForeignKeyField(
        "models.RekordboxTrack", related_name="playlist_tracks"
    )
