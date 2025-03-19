async def test_add_tracks(rekordbox_playlist_factory, rekordbox_track_factory):
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
