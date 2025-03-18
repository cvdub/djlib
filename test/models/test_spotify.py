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
