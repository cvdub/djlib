from ..clients import SpotifyClient
from ..models import SpotifyPlaylist
from .abstract import Library


class SpotifyLibrary(Library):
    client_class = SpotifyClient
    playlist_class = SpotifyPlaylist
