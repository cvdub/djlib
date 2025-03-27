import pytest
from djlib.libraries import SpotifyLibrary
from djlib.models import SpotifyPlaylist


@pytest.fixture
async def library(database):
    async with SpotifyLibrary() as library:
        yield library


async def test_refresh_creates_playlists(library):
    assert await SpotifyPlaylist.exists() is False
    await library.refresh()
    playlists = await SpotifyPlaylist.all()
    assert playlists == [
        SpotifyPlaylist(
            id=1,
            external_id="3LY6zUsZnigfz2fE3vSHbS",
            name="djlib test",
            snapshot_id="AAAAB0Y4AJJhwEDQtWhE0Ppmo4F2l2VO",
        ),
        SpotifyPlaylist(
            id=2,
            external_id="7J1K9u2nnco5Ul4I7OAIcp",
            name="My Playlist #2",
            snapshot_id="AAAAAbUV+IiAInfd0bXbjQVDWnYzxAyI",
        ),
        SpotifyPlaylist(
            id=3,
            external_id="6ZjBXWsTRXWUav7gT1xAmf",
            name="My Playlist #3",
            snapshot_id="AAAAAW3PoKrLHNDe0m74BPZ/yvIUfkd0",
        ),
        SpotifyPlaylist(
            id=4,
            external_id="14pqScfLyztytZLjse99Gz",
            name="My Playlist #4",
            snapshot_id="AAAAAXbaP7kKf9T7Ern67R0YySYwvYFo",
        ),
        SpotifyPlaylist(
            id=5,
            external_id="6cJOTWnSF4J9l88DIdjkxA",
            name="My Playlist #5",
            snapshot_id="AAAAAXD7O8aNatqkNeJUO9TBicJGeIcx",
        ),
    ]

    track_titles = await playlists[0].tracks.all().values_list("title", flat=True)
    assert track_titles == [
        "Mareación",
        "Sempiternal",
        "All the Way",
        "This Way",
        "Corvus Corax",
        "Soul Ricochet",
        "Grandiloquence",
        "In the Stars",
        "Aleatory",
        "Over the Ocean",
        "Grace",
        "Feel You in My Heart",
        "Contact",
        "The Majesty",
        "Remain",
        "Broken Sun",
        "Eulogy",
        "Breath of Shadows",
        "Loose",
        "Soothe",
        "Red Horizon",
        "Lives to Live",
        "Infinities",
        "Winter Leaves",
        "All the Light",
        "Abiogenesis",
        "Noumenon",
        "Me She",
        "Flight of Flame",
        "The Reveal",
        "Gimme That Hope",
        "Curiosity",
        "A Little More Free",
        "Outpost Aurora",
        "Parallels",
        "Lucid Interval",
        "Thunder Shadow",
        "Redacter",
        "Formulates in Darkness",
        "Water Chandelier",
        "Bodhicitta",
        "Time Reel",
        "Heavenly Light",
        "Sepulcher",
        "Repose",
        "Ganymede",
        "Nartha",
        "Planet Life",
        "Suns of Midnight",
        "Each Other",
        "Kalide",
        "Eternally",
        "Fate Shadow",
        "Dilection",
        "Colony Collapse",
        "39 Circles",
        "Golden Thread",
        "Perceiver",
        "Falling Tao",
        "Release",
        "Fog Lantern",
        "Journey to the Eye of the Whale",
        "Rain On the World",
        "Blast Off",
        "The Plastic People",
        "Crossing Over",
        "Requiem",
        "The River",
        "Want",
        "Dune's Lullaby",
        "Absolution",
        "Fiesta - Remastered",
    ]


async def test_refresh_deletes_playlists_removed_from_client(
    library, spotify_playlist_factory
):
    deleted_playlist = await spotify_playlist_factory()
    await library.refresh()
    assert await SpotifyPlaylist.filter(id=deleted_playlist.id).exists() is False


async def test_refresh_renames_playlists(library, spotify_playlist_factory):
    renamed_playlists = (
        await spotify_playlist_factory(
            external_id="3LY6zUsZnigfz2fE3vSHbS", name="Foo"
        ),
        await spotify_playlist_factory(
            external_id="6ZjBXWsTRXWUav7gT1xAmf", name="Bar"
        ),
    )
    await library.refresh()
    for playlist in renamed_playlists:
        await playlist.refresh_from_db()

    assert renamed_playlists[0].name == "djlib test"
    assert renamed_playlists[1].name == "My Playlist #3"
