import asyncio
import time
from collections.abc import Generator
from pathlib import Path
from typing import List, Self

import httpx
from librespot.core import Session
from librespot.zeroconf import ZeroconfServer

from ..config import Config
from ..logging import logger
from ..models import SpotifyPlaylist, SpotifyTrack
from .abstract import Client

SPOTIFY_API_URL = "https://api.spotify.com/v1/"
CONCURRENT_API_CALLS = 2


class SpotifyClient(Client):
    """Class for interfacing with a Spotify library."""

    def __init__(self):
        self._api_semaphore = asyncio.Semaphore(CONCURRENT_API_CALLS)
        self._librespot_credentials_file = Config.cache_directory / Path(
            "credentials.json"
        )

    async def connect(self) -> None:
        # HTTPX
        self._httpx_client = httpx.AsyncClient(http2=True)

        # Librespot
        if not self._librespot_credentials_file.exists():
            await asyncio.to_thread(lambda: self._get_credentials())

        librespot_config = Session.Configuration.Builder().set_stored_credential_file(
            self._librespot_credentials_file
        )
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._librespot_session = await asyncio.to_thread(
                    lambda: Session.Builder(librespot_config).stored_file().create()
                )
            except Exception:
                if attempt == max_retries - 1:  # Last attempt
                    raise  # Re-raise the last exception
                await asyncio.sleep(1)  # Wait before retrying
            else:
                break

    def get_credentials(self) -> None:
        zeroconf_builder = ZeroconfServer.Builder()
        zeroconf_builder.set_device_name("djlib")
        zeroconf_builder.conf.stored_credentials_file = self._librespot_credentials_file
        zeroconf = zeroconf_builder.create()
        logger.debug("Started Zeroconf server")
        logger.info('Select "djlib" in Spotify client to authenticate')
        while True:
            time.sleep(1)
            logger.debug("Authenticating...")
            if zeroconf.has_valid_session():
                logger.debug("Got Spotify credentials!")
                zeroconf.close_session()
                zeroconf.close()
                while not self._librespot_credentials_file.exists():
                    time.sleep(0.1)  # Give credentials file time to save

                return

    async def close(self) -> None:
        self._librespot_session.close()
        await self._httpx_client.aclose()

    async def _api_request(self, endpoint: str) -> dict:
        if not endpoint.startswith(SPOTIFY_API_URL):
            endpoint = SPOTIFY_API_URL + endpoint

        token = self._librespot_session.tokens().get("playlist-read-private")
        async with self._api_semaphore:
            response = await self._httpx_client.get(
                endpoint, headers={"Authorization": f"Bearer {token}"}
            )

        response.raise_for_status()
        return response.json()

    async def _api_items(self, endpoint: str) -> List[dict]:
        response = await self._api_request(endpoint)
        while True:
            for item in response["items"]:
                yield item

            if response["next"]:
                response = await self._api_request(response["next"])
            else:
                break

    async def get_playlists(self) -> Generator[SpotifyPlaylist]:
        async for item in self._api_items("me/playlists"):
            yield SpotifyPlaylist(
                external_id=item["id"],
                name=item["name"],
                snapshot_id=item["snapshot_id"],
            )

    async def get_playlist_tracks(
        self, playlist: SpotifyPlaylist
    ) -> Generator[SpotifyTrack]:
        async for item in self._api_items(
            f"playlists/{playlist.external_id}/tracks?market=US"
            "&fields=items("
            "track(id,"
            "name,"
            "track_number,"
            "disc_number,"
            "is_playable,"
            "external_ids(isrc),"
            "artists(name),"
            "album(name,artists(name),images(url)),"
            "linked_from)"
            ",is_local),"
            "next"
        ):
            if not item["track"]:
                continue

            if not item["track"]["id"]:
                # TODO: Handle local tracks
                # - Try making an ID from the ISRC
                logger.warning(f"No ID found for {item['track']['name']}")
                continue

            try:
                album_artist = item["track"]["album"]["artists"][0]["name"]
            except IndexError:
                album_artist = None

            try:
                album_art_url = item["track"]["album"]["images"][0]["url"]
            except IndexError:
                album_art_url = None

            isrc = item["track"]["external_ids"].get("isrc")
            if isrc:
                isrc = isrc.replace("-", "")

            try:
                track_number = int(item["track"]["track_number"])
            except ValueError:
                track_number = 1

            if track_number < 1:
                track_number = 1

            try:
                disc_number = int(item["track"]["disc_number"])
            except ValueError:
                disc_number = 1

            if disc_number < 1:
                disc_number = 1

            yield SpotifyTrack(
                external_id=item["track"]["id"],
                title=item["track"]["name"],
                artist=item["track"]["artists"][0]["name"],
                album=item["track"]["album"]["name"],
                album_artist=album_artist,
                track_number=track_number,
                disc_number=disc_number,
                isrc=isrc,
                is_local=item["is_local"],
                is_playable=item["track"].get("is_playable"),
                album_art_url=album_art_url,
            )
