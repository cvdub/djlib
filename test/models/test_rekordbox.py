from pathlib import Path

from djlib.models import RekordboxTrack


class TestRekordboxPlaylist:
    async def test_add_tracks(
        self, rekordbox_playlist_factory, rekordbox_track_factory
    ):
        playlist = await rekordbox_playlist_factory()
        await playlist.save()
        for i in range(5):
            track = await rekordbox_track_factory(title=str(i))
            await playlist.add_tracks(track)

        assert await playlist.tracks.all().values_list("title", flat=True) == [
            "0",
            "1",
            "2",
            "3",
            "4",
        ]

        new_track = await rekordbox_track_factory(title="5")
        await playlist.add_tracks(new_track, index=1)
        assert await playlist.tracks.all().values_list("title", flat=True) == [
            "0",
            "5",
            "1",
            "2",
            "3",
            "4",
        ]

        new_tracks = [
            await rekordbox_track_factory(title="6"),
            await rekordbox_track_factory(title="7"),
        ]

        await playlist.add_tracks(*new_tracks, delete_existing=True)
        assert await playlist.tracks.all().values_list("title", flat=True) == [
            "6",
            "7",
        ]


class TestRekordboxTrack:
    def test_from_file(self, track_path):
        track = RekordboxTrack.from_file(track_path)
        assert track.title == "Torrid Soul"
        assert track.artist == "HVOB"
        assert track.album == "Silk"
        assert track.album_artist == "HVOB"
        assert track.track_number == 3
        assert track.disc_number == 1
        assert track.isrc == "DEUE11730222"
        assert track.path == track_path

    def test_import_path(self, track_path):
        track = RekordboxTrack.from_file(track_path)
        assert str(track.import_path()).endswith("music/HVOB/Silk/03 Torrid Soul.mp3")
        assert str(track.import_path(unique=True)).endswith(
            "music/HVOB/Silk/03 Torrid Soul (2).mp3"
        )
