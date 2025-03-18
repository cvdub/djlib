from tortoise import fields
from tortoise.validators import MinLengthValidator

from .abstract import Playlist, PlaylistTrack, Track


class SpotifyPlaylist(Playlist):
    external_id = fields.CharField(
        max_length=22, validators=[MinLengthValidator(22)], unique=True
    )
    snapshot_id = fields.CharField(
        max_length=32, null=True, validators=[MinLengthValidator(32)]
    )
    playlist_tracks: fields.ReverseRelation["SpotifyPlaylistTrack"]


class SpotifyTrack(Track):
    external_id = fields.CharField(
        max_length=22, validators=[MinLengthValidator(22)], unique=True
    )
    is_local = fields.BooleanField(default=False)
    is_playable = fields.BooleanField(default=True)
    album_art_url = fields.CharField(max_length=255, null=True)


class SpotifyPlaylistTrack(PlaylistTrack):
    playlist: fields.ForeignKeyRelation[SpotifyPlaylist] = fields.ForeignKeyField(
        "models.SpotifyPlaylist", related_name="playlist_tracks"
    )
    track: fields.ForeignKeyRelation[SpotifyTrack] = fields.ForeignKeyField(
        "models.SpotifyTrack", related_name="playlist_tracks"
    )
