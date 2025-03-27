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
    assert [(track.title, track.isrc) async for track in tracks] == [
        ("Mareación", "QZNJW2349474"),
        ("Sempiternal", "QZNJW2349475"),
        ("All the Way", "QZNJW2349476"),
        ("This Way", "QZNJW2349477"),
        ("Corvus Corax", "QZNJW2349478"),
        ("Soul Ricochet", "QZNJW2349479"),
        ("Grandiloquence", "QZNJW2349480"),
        ("In the Stars", "QZNJW2349481"),
        ("Aleatory", "QZNJW2349482"),
        ("Over the Ocean", "QZNJW2349483"),
        ("Grace", "QZNJW2349484"),
        ("Feel You in My Heart", "QZNJW2349485"),
        ("Contact", "QZNJW2349486"),
        ("The Majesty", "QZNJW2349487"),
        ("Remain", "USCGH1974089"),
        ("Broken Sun", "uscgh1974090"),
        ("Eulogy", "uscgh1974091"),
        ("Breath of Shadows", "uscgh1974092"),
        ("Loose", "USCGH1974093"),
        ("Soothe", "USCGH1974094"),
        ("Red Horizon", "USCGH1974095"),
        ("Lives to Live", "USCGH1974096"),
        ("Infinities", "USCGH1974097"),
        ("Winter Leaves", "USCGH1974098"),
        ("All the Light", "USCGH1974099"),
        ("Abiogenesis", "USCGH1974100"),
        ("Noumenon", "USCGH1974101"),
        ("Me She", "USCGH1974102"),
        ("Flight of Flame", "USCGH1974103"),
        ("The Reveal", "USCGH1974104"),
        ("Gimme That Hope", "USDY41754696"),
        ("Curiosity", "USDY41754697"),
        ("A Little More Free", "USDY41754698"),
        ("Outpost Aurora", "USDY41754699"),
        ("Parallels", "USDY41754700"),
        ("Lucid Interval", "USDY41754701"),
        ("Thunder Shadow", "USDY41754702"),
        ("Redacter", "USDY41754703"),
        ("Formulates in Darkness", "USDY41754704"),
        ("Water Chandelier", "USDY41754705"),
        ("Bodhicitta", "USDY41754706"),
        ("Time Reel", "USDY41754707"),
        ("Heavenly Light", "USDY41754708"),
        ("Sepulcher", "USDY41754709"),
        ("Repose", "USDY41754710"),
        ("Ganymede", "USA2P1520202"),
        ("Nartha", "USA2P1520204"),
        ("Planet Life", "USA2P1520205"),
        ("Suns of Midnight", "USA2P1520203"),
        ("Each Other", "USA2P1520206"),
        ("Kalide", "USA2P1520207"),
        ("Eternally", "USA2P1520208"),
        ("Fate Shadow", "USA2P1520209"),
        ("Dilection", "USA2P1520210"),
        ("Colony Collapse", "USA2P1520211"),
        ("39 Circles", "USA2P1520212"),
        ("Golden Thread", "USA2P1520213"),
        ("Perceiver", "USHM91325236"),
        ("Falling Tao", "USHM91325237"),
        ("Release", "USHM91325238"),
        ("Fog Lantern", "USHM91325239"),
        ("Journey to the Eye of the Whale", "USHM91325240"),
        ("Rain On the World", "USHM91325241"),
        ("Blast Off", "USHM91325242"),
        ("The Plastic People", "USHM91325243"),
        ("Crossing Over", "USHM91325244"),
        ("Requiem", "USHM91325245"),
        ("The River", "USHM91325246"),
        ("Want", "USHM91325247"),
        ("Dune's Lullaby", "USHM91325248"),
        ("Absolution", "USHM91325249"),
        ("Fiesta - Remastered", "USEAX1703135"),  # Relinked from USEAX1100398
    ]
