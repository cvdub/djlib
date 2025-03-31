from djlib.models import Track


class TestTrack:
    def test_from_file(self, track_path):
        track = Track.from_file(track_path)
        assert track.title == "Torrid Soul"
        assert track.artist == "HVOB"
        assert track.album_artist == "HVOB"
        assert track.album == "Silk"
        assert track.track_number == 3
        assert track.disc_number == 1
        assert track.isrc == "DEUE11730222"
