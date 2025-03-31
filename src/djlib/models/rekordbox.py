from pathlib import Path
from typing import Self

from tortoise import fields

from ..config import Config
from .abstract import Playlist, PlaylistTrack, Track


class RekordboxPlaylist(Playlist):
    external_id = fields.CharField(max_length=255, unique=True)
    playlist_tracks: fields.ReverseRelation["RekordboxPlaylistTrack"]


class RekordboxTrack(Track):
    external_id = fields.CharField(max_length=255, unique=True)
    path = fields.CharField(max_length=255, unique=True)

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
