from ..clients import RekordboxClient
from ..models import RekordboxPlaylist
from .abstract import Library


class RekordboxLibrary(Library):
    client_class = RekordboxClient
    playlist_class = RekordboxPlaylist
