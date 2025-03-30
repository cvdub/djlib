from ..clients import RekordboxClient
from ..models import RekordboxPlaylist, RekordboxTrack
from .abstract import Library


class RekordboxLibrary(Library):
    client_class = RekordboxClient
    playlists = RekordboxPlaylist
    tracks = RekordboxTrack
