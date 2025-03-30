from ..clients import SpotifyClient
from ..models import SpotifyPlaylist, SpotifyTrack
from .abstract import Library


class SpotifyLibrary(Library):
    client_class = SpotifyClient
    playlists = SpotifyPlaylist
    tracks = SpotifyTrack
