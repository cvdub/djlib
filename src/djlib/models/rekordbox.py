from tortoise import fields

from .abstract import Playlist, PlaylistTrack, Track


class RekordboxPlaylist(Playlist):
    external_id = fields.CharField(max_length=255, unique=True)
    playlist_tracks: fields.ReverseRelation["RekordboxPlaylistTrack"]


class RekordboxTrack(Track):
    external_id = fields.CharField(max_length=255, unique=True)
    path = fields.CharField(max_length=255, unique=True)


class RekordboxPlaylistTrack(PlaylistTrack):
    playlist: fields.ForeignKeyRelation[RekordboxPlaylist] = fields.ForeignKeyField(
        "models.RekordboxPlaylist", related_name="playlist_tracks"
    )
    track: fields.ForeignKeyRelation[RekordboxTrack] = fields.ForeignKeyField(
        "models.RekordboxTrack", related_name="playlist_tracks"
    )
