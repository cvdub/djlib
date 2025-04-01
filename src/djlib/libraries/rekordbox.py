import asyncio

from ..clients import RekordboxClient
from ..models import RekordboxPlaylist, RekordboxTrack
from .abstract import Library


class RekordboxLibrary(Library):
    client_class = RekordboxClient
    playlists = RekordboxPlaylist
    tracks = RekordboxTrack

    async def _refresh_non_playlist_tracks(self) -> None:
        # Delete cached tracks with no playlists
        track_ids = (
            await RekordboxTrack.filter(playlist_tracks=None)
            .all()
            .values_list("id", flat=True)
        )
        await RekordboxTrack.filter(id__in=track_ids).all().delete()

        # Save updated list of tracks with no playlist
        async with asyncio.TaskGroup() as tg:
            async for track in self._client.get_non_playlist_tracks():
                tg.create_task(track.set_id_and_save())
