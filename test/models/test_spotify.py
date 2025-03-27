from djlib.models import SpotifyPlaylist


def test_differs_from():
    p1 = SpotifyPlaylist(snapshot_id="1")
    p2 = SpotifyPlaylist(snapshot_id="1")
    assert p1.differs_from(p2) is False

    p2.snapshot_id = "2"
    assert p1.differs_from(p2)


async def test_update_to_match(spotify_playlist_factory):
    p1 = await spotify_playlist_factory(name="foo")
    p2 = await spotify_playlist_factory(name="bar", save=False)
    await p1.update_to_match(p2)
    assert p1.name == "bar"
    assert p1.snapshot_id == p2.snapshot_id


async def test_add_tracks(spotify_playlist_factory, spotify_track_factory):
    playlist = await spotify_playlist_factory()
    await playlist.save()
    for i in range(5):
        track = await spotify_track_factory(title=str(i))
        await playlist.add_tracks(track)

    assert await playlist.tracks.all().values_list("title", flat=True) == [
        "0",
        "1",
        "2",
        "3",
        "4",
    ]

    new_track = await spotify_track_factory(title="5")
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
        await spotify_track_factory(title="6"),
        await spotify_track_factory(title="7"),
    ]

    await playlist.add_tracks(*new_tracks, delete_existing=True)
    assert await playlist.tracks.all().values_list("title", flat=True) == [
        "6",
        "7",
    ]


async def test_set_id_and_save(spotify_track_factory):
    track = await spotify_track_factory(title="Bar", save=False)
    assert track.id is None
    await track.set_id_and_save()
    assert track.id == 1
    assert track.title == "Bar"

    track.id = None
    track.title = "Foo"
    await track.set_id_and_save()
    assert track.id == 1
    await track.refresh_from_db()
    assert track.title == "Foo"

    new_track = await spotify_track_factory(
        external_id=track.external_id, title="Baz", save=False
    )
    await new_track.set_id_and_save()
    assert new_track.pk == 1
    await track.refresh_from_db()
    assert track.title == "Baz"
