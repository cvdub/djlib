import pytest
from djlib.clients import SpotifyClient
from djlib.models import SpotifyPlaylist


@pytest.fixture
async def client(scope="file"):
    async with SpotifyClient() as client:
        yield client


async def test_api_request(client):
    for endpoint in (
        "tracks/2nyaXSqyJnjwPaYjZocLcE",
        # Also works with full URL (needed for NEXT calls)
        "https://api.spotify.com/v1/tracks/2nyaXSqyJnjwPaYjZocLcE",
    ):
        response = await client._api_request(endpoint)
        assert response["name"] == "Lives to Live"


async def test_get_playlists(client):
    playlists = [playlist async for playlist in client.get_playlists()]
    assert playlists == [
        SpotifyPlaylist(
            external_id="6cJOTWnSF4J9l88DIdjkxA",
            name="My Playlist #5",
            snapshot_id="AAAAAXD7O8aNatqkNeJUO9TBicJGeIcx",
        ),
        SpotifyPlaylist(
            external_id="14pqScfLyztytZLjse99Gz",
            name="My Playlist #4",
            snapshot_id="AAAAAXbaP7kKf9T7Ern67R0YySYwvYFo",
        ),
        SpotifyPlaylist(
            external_id="6ZjBXWsTRXWUav7gT1xAmf",
            name="My Playlist #3",
            snapshot_id="AAAAAW3PoKrLHNDe0m74BPZ/yvIUfkd0",
        ),
        SpotifyPlaylist(
            external_id="7J1K9u2nnco5Ul4I7OAIcp",
            name="My Playlist #2",
            snapshot_id="AAAAAbUV+IiAInfd0bXbjQVDWnYzxAyI",
        ),
        SpotifyPlaylist(
            external_id="3LY6zUsZnigfz2fE3vSHbS",
            name="djlib test",
            snapshot_id="AAAAB0Y4AJJhwEDQtWhE0Ppmo4F2l2VO",
        ),
    ]


async def test_get_playlist_tracks(client, spotify_playlist_factory):
    playlist = await spotify_playlist_factory(
        external_id="3LY6zUsZnigfz2fE3vSHbS", save=False
    )
    tracks = client.get_playlist_tracks(playlist)
    assert [track.title async for track in tracks] == [
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
    ]
