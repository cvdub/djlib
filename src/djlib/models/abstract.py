from typing import List, Optional

from tortoise import Tortoise, fields, transactions
from tortoise.models import Model
from tortoise.validators import MinLengthValidator, MinValueValidator


class Playlist(Model):
    external_id = fields.CharField(max_length=255, unique=True)
    name = fields.CharField(max_length=255, unique=True)
    playlist_tracks: fields.ReverseRelation["PlaylistTrack"]

    class Meta:
        abstract = True
        indexes = ("external_id",)

    def __str__(self) -> str:
        return self.name

    @property
    def _track_model(self) -> type["PlaylistTrack"]:
        track_class_name = self.__class__.__name__.replace("Playlist", "Track")
        return Tortoise.apps.get("models").get(track_class_name)

    @property
    def _playlist_track_model(self) -> type["PlaylistTrack"]:
        playlist_track_class_name = self.__class__.__name__ + "Track"
        return Tortoise.apps.get("models").get(playlist_track_class_name)

    @property
    def tracks(self):
        return self._track_model.filter(playlist_tracks__playlist=self).order_by(
            "playlist_tracks__index"
        )

    @transactions.atomic()
    async def add_tracks(
        self,
        *tracks: List[type["Track"]],
        index: Optional[int] = None,
        delete_existing=False,
    ) -> None:
        """Add TRACKS to this playlist, starting at INDEX.

        If INDEX is None, TRACKS are added to the end of the playlist.
        If DELETE_EXISTING is True, existing playlist tracks are replaced with TRACKS.
        """
        if delete_existing:
            await self.playlist_tracks.all().delete()
            playlist_tracks = []
        else:
            playlist_tracks = list(await self.playlist_tracks.all())

        if index is None:
            index = len(playlist_tracks)

        new_playlist_tracks = [
            self._playlist_track_model(playlist=self, track=track) for track in tracks
        ]
        playlist_tracks[index:index] = new_playlist_tracks

        # Update playlist track indices
        for i, playlist_track in enumerate(playlist_tracks):
            if playlist_track.index != i:
                playlist_track.index = i

        # Save indices in reverse to avoid unique index validation error
        for playlist_track in reversed(playlist_tracks):
            await playlist_track.save()


class Track(Model):
    title = fields.CharField(max_length=255)
    artist = fields.CharField(max_length=255, null=True)
    album = fields.CharField(max_length=255, null=True)
    album_artist = fields.CharField(max_length=255, null=True)
    track_number = fields.SmallIntField(null=True, validators=[MinValueValidator(1)])
    disc_number = fields.SmallIntField(null=True, validators=[MinValueValidator(1)])
    isrc = fields.CharField(
        max_length=12, null=True, validators=[MinLengthValidator(12)]
    )

    class Meta:
        abstract = True
        indexes = ("external_id", "isrc")

    def __str__(self) -> str:
        return self.title


class PlaylistTrack(Model):
    playlist: fields.ForeignKeyRelation[Playlist] = fields.ForeignKeyField(
        "models.Playlist", related_name="playlist_tracks"
    )
    track: fields.ForeignKeyRelation[Track] = fields.ForeignKeyField(
        "models.Track", related_name="playlist_tracks"
    )
    index = fields.SmallIntField(validators=[MinValueValidator(0)])

    class Meta:
        abstract = True
        unique_together = ("playlist", "index")
