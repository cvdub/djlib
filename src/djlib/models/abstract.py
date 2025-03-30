from enum import Enum
from typing import List, Optional, Self

from tortoise import Tortoise, fields, transactions
from tortoise.models import Model
from tortoise.queryset import QuerySet
from tortoise.validators import MinLengthValidator, MinValueValidator


class PlaylistStatus(str, Enum):
    NEW = "new"
    SYNCED = "synced"
    IGNORED = "ignored"


class Playlist(Model):
    external_id = fields.CharField(max_length=255, unique=True)
    name = fields.CharField(max_length=255, unique=True)
    status = fields.CharEnumField(PlaylistStatus, default=PlaylistStatus.NEW)
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

    def differs_from(self, other_playlist: type["Playlist"]) -> bool:
        """Return True if the metadata for this playlist matches OTHER_PLAYLIST.

        This defaults to True in the base case, but can be extended by other back
        ends that contain specific fields to indicate when a playlist has changed.
        """
        return True

    async def update_to_match(
        self, other_playlist: type["Playlist"], save=True
    ) -> None:
        """Updates the metadata for this playlist to match OTHER_PLAYLIST."""
        self.name = other_playlist.name
        if save:
            await self.save()


class Track(Model):
    external_id = fields.CharField(max_length=255, unique=True)
    title = fields.CharField(max_length=255)
    artist = fields.CharField(max_length=255, null=True)
    album = fields.CharField(max_length=255, null=True)
    album_artist = fields.CharField(max_length=255, null=True)
    track_number = fields.SmallIntField(null=True, validators=[MinValueValidator(1)])
    disc_number = fields.SmallIntField(null=True, validators=[MinValueValidator(0)])
    isrc = fields.CharField(
        max_length=12, null=True, validators=[MinLengthValidator(12)]
    )

    class Meta:
        abstract = True
        indexes = ("external_id", "isrc")

    def __str__(self) -> str:
        return self.title

    @transactions.atomic()
    async def set_id_and_save(self) -> None:
        existing_id = await self.__class__.filter(
            external_id=self.external_id
        ).values_list("id", flat=True)
        if existing_id:
            self.id = existing_id[0]
            force_update = True
        else:
            force_update = False

        await self.save(force_update=force_update)

    @classmethod
    def in_synced_playlists(cls) -> QuerySet[Self]:
        return cls.filter(
            playlist_tracks__playlist__status=PlaylistStatus.SYNCED
        ).distinct()


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
