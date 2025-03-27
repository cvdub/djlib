from ..clients import SpotifyClient
from ..logging import logger
from ..models import SpotifyPlaylist
from .abstract import Library


class SpotifyLibrary(Library):
    client_class = SpotifyClient
    playlist_class = SpotifyPlaylist

    async def _refresh_playlist(self, client_playlist: SpotifyPlaylist) -> None:
        logger.debug(
            f"Refreshing {self.playlist_class.__name__} {client_playlist.name}"
        )
        local_playlist, created = await self.playlist_class.update_or_create(
            external_id=client_playlist.external_id,
            defaults={"name": client_playlist.name},
        )
        if local_playlist.snapshot_id == client_playlist.snapshot_id:
            logger.debug(f"No changes to SpotifyPlaylist {local_playlist.name}")
        else:
            await self._refresh_playlist_tracks(local_playlist)
            local_playlist.snapshot_id = client_playlist.snapshot_id
            await local_playlist.save()

        logger.debug(
            f"Finished refreshing {self.playlist_class.__name__} {client_playlist.name}"
        )
