import asyncio
import random
import time
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import AsyncGenerator

import httpx
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.core import Session
from librespot.metadata import TrackId
from librespot.zeroconf import ZeroconfServer
from mutagen.id3 import (
    APIC,
    ID3,
    TALB,
    TIT2,
    TPE1,
    TPE2,
    TPOS,
    TRCK,
    TSRC,
    TXXX,
    Encoding,
)
from pydub import AudioSegment

from ..config import Config
from ..logging import logger
from ..models import SpotifyPlaylist, SpotifyTrack
from .abstract import Client, TrackExportError

SPOTIFY_API_URL = "https://api.spotify.com/v1/"
CONCURRENT_API_CALLS = 1
CONCURRENT_DOWNLOADS = 2
DOWNLOAD_RETRIES = 10
DOWNLOAD_RETRY_BASE_WAIT_TIME = 1  # seconds
TRACK_STREAM_LOCK_DURATION = 10  # seconds

CHUNK_SIZE = 65_536


class InvalidSpotifyTrackData(Exception):
    pass


class SpotifyClient(Client):
    """Class for interfacing with a Spotify library."""

    _api_semaphore = asyncio.Semaphore(CONCURRENT_API_CALLS)
    _track_stream_semaphore = asyncio.Semaphore(CONCURRENT_DOWNLOADS)
    _last_track_stream_failure = 0

    def __init__(self):
        self._librespot_credentials_file = Config.cache_directory / Path(
            "credentials.json"
        )

    async def connect(self) -> None:
        logger.debug(f"Starting {self}")
        # HTTPX
        self._httpx_client = httpx.AsyncClient(http2=True)

        # Librespot
        if not self._librespot_credentials_file.exists():
            await asyncio.to_thread(self._get_credentials)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._librespot_session = await asyncio.to_thread(
                    self._create_librespot_session
                )
            except Exception:
                if attempt == max_retries - 1:  # Last attempt
                    raise
                await asyncio.sleep(1)  # Wait before retrying
            else:
                break

    def _get_credentials(self) -> None:
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

    def _create_librespot_session(self) -> Session:
        librespot_config = Session.Configuration.Builder().set_stored_credential_file(
            self._librespot_credentials_file
        )
        return Session.Builder(librespot_config).stored_file().create()

    async def close(self) -> None:
        logger.debug(f"Closing {self}")
        self._librespot_session.close()
        await self._httpx_client.aclose()

    async def _api_request(self, endpoint: str) -> dict:
        # TODO: Add retry for 500 error
        if not endpoint.startswith(SPOTIFY_API_URL):
            endpoint = SPOTIFY_API_URL + endpoint

        token = self._librespot_session.tokens().get("playlist-read-private")
        async with self._api_semaphore:
            response = await self._httpx_client.get(
                endpoint, headers={"Authorization": f"Bearer {token}"}
            )

        try:
            response.raise_for_status()
        except Exception:
            logger.error(response)
            raise

        return response.json()

    async def _api_items(self, endpoint: str) -> AsyncGenerator[dict, None]:
        response = await self._api_request(endpoint)
        while True:
            for item in response["items"]:
                yield item

            if response["next"]:
                response = await self._api_request(response["next"])
            else:
                break

    async def get_playlists(self) -> AsyncGenerator[SpotifyPlaylist, None]:
        async for item in self._api_items("me/playlists"):
            yield SpotifyPlaylist(
                external_id=item["id"],
                name=item["name"],
                snapshot_id=item["snapshot_id"],
            )

    async def get_playlist_tracks(
        self, playlist: SpotifyPlaylist
    ) -> AsyncGenerator[SpotifyTrack, None]:
        items = []
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
            if item["track"]:
                items.append(item)

        # Collect relinked tracks
        relinked_track_ids = []
        for item in items:
            if "linked_from" in item["track"]:
                relinked_track_ids.append(item["track"]["id"])

        relinked_items_map = {}
        if relinked_track_ids:
            logger.debug(f"Relinking {len(relinked_track_ids)} tracks in {playlist}")

        # Pull metadata for relinked tracks in batches of 100
        for i in range(0, len(relinked_track_ids), 99):
            if track_ids := relinked_track_ids[i : 1 + 99]:
                relinked_items = await self._api_request(
                    f"tracks?ids={','.join(track_ids)}&market=US"
                )
                for item in relinked_items["tracks"]:
                    relinked_items_map[item["id"]] = {
                        "track": item,
                        "is_local": item["is_local"],
                    }

        for item in items:
            try:
                item = relinked_items_map[item["track"]["id"]]
            except KeyError:
                pass

            try:
                yield self._track_from_api_item(item)
            except InvalidSpotifyTrackData as e:
                logger.warning(str(e))
                continue

    def _track_from_api_item(self, item: dict) -> SpotifyTrack:
        if not item["track"]:
            raise InvalidSpotifyTrackData(f'No "track" in Spotify API item {item}')

        if not item["track"]["id"]:
            # TODO: Handle local tracks
            # - Try making an ID from the ISRC
            raise InvalidSpotifyTrackData(
                f"No ID found for Spotify API track {item['track']['name']}"
            )

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

        if disc_number < 0:
            disc_number = 0

        return SpotifyTrack(
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

    async def export_track(self, track: SpotifyTrack, export_directory: Path) -> Path:
        logger.debug(f"Exporting {track}")
        if not track.is_playable:
            raise TrackExportError(f"{track} is not playable, skipping export")

        retry_attempt = 1

        while True:
            # Wait if we're in the lock period
            time_since_failure = time.time() - self._last_track_stream_failure
            if time_since_failure < TRACK_STREAM_LOCK_DURATION:
                wait_time = TRACK_STREAM_LOCK_DURATION - time_since_failure
                logger.debug(f"Waiting {wait_time:.1f}s before retrying track stream")
                await asyncio.sleep(wait_time)

            try:
                async with self._track_stream_semaphore:
                    audio_bytes = await asyncio.to_thread(
                        self._get_track_stream,
                        track,
                    )
            except TrackExportError as e:
                self._last_track_stream_failure = time.time()
                if retry_attempt >= DOWNLOAD_RETRIES:
                    raise
                else:
                    # Exponential backoff with jitter
                    wait_time = DOWNLOAD_RETRY_BASE_WAIT_TIME * (
                        2 ** (retry_attempt - 1)
                    ) + random.uniform(0, 1)
                    logger.warning(
                        f"[{retry_attempt}/{DOWNLOAD_RETRIES}] {e}. Waiting {wait_time:.1f}s before retry."
                    )
                    await asyncio.sleep(wait_time)
                    retry_attempt += 1
            else:
                break

        logger.debug(f"Converting {track} to MP3")
        audio = await asyncio.to_thread(
            AudioSegment.from_file, audio_bytes, format="ogg"
        )
        export_path = export_directory / f"{track.isrc}.mp3"
        await asyncio.to_thread(
            audio.export,
            export_path,
            format="mp3",
            parameters=["-q:a", "0"],
        )

        logger.debug(f"Setting ID3 tags on {track}")
        audio = ID3(export_path)
        audio.add(TIT2(text=track.title, encoding=Encoding.UTF8))
        if track.artist:
            audio.add(TPE1(text=track.artist, encoding=Encoding.UTF8))

        if track.album:
            audio.add(TALB(text=track.album, encoding=Encoding.UTF8))

        if track.album_artist:
            audio.add(TPE2(text=track.album_artist, encoding=Encoding.UTF8))

        if track.track_number is not None:
            audio.add(TRCK(text=str(track.track_number), encoding=Encoding.UTF8))

        if track.disc_number is not None:
            audio.add(TPOS(text=str(track.disc_number), encoding=Encoding.UTF8))

        audio.add(TSRC(text=track.isrc, encoding=Encoding.UTF8))
        audio.add(TXXX(desc="spotify_uris", text=track.external_id))

        if track.album_art_url:
            logger.debug(f"Getting album art for {track}")
            response = await self._httpx_client.get(track.album_art_url)
            if response.status_code == 200:
                audio.add(
                    APIC(
                        data=response.content,
                        encoding=Encoding.UTF8,
                        mime="image/jpeg",
                        type=3,
                        desc="0",
                    )
                )
            else:
                logger.error(f"Failed to get album art for {track}: {response}")

        await asyncio.to_thread(audio.save)

        # TODO: Add config options for normalization
        logger.debug(f"Normalizing {export_path}")
        await asyncio.create_subprocess_exec(
            "mp3gain",
            "-e",
            "-r",
            "-k",
            "-d",
            "6",
            "-p",
            "-s",
            "r",
            export_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        logger.debug(f"Finished exporting {track}")

        return export_path

    def _get_track_stream(self, track: SpotifyTrack) -> BytesIO:
        try:
            track_stream = self._librespot_session.content_feeder().load(
                TrackId.from_base62(track.external_id),
                VorbisOnlyAudioQuality(AudioQuality.VERY_HIGH),
                False,  # Pre-load
                None,
            )
            total_size = track_stream.input_stream.size
            downloaded = 0
            audio_bytes = BytesIO()
            last_progress_percentage = 0
            fail_count = 0
            while True:
                data = track_stream.input_stream.stream().read(CHUNK_SIZE)
                if not data:
                    fail_count += 1
                    if fail_count > 5:
                        break

                downloaded += len(data)
                audio_bytes.write(data)

                percent_complete = round(downloaded / total_size * 100)
                if percent_complete > last_progress_percentage + 10:
                    logger.debug(
                        f"[{percent_complete}%] Downloading track stream for {track}"
                    )
                    last_progress_percentage = percent_complete

            audio_bytes.seek(0)
            return audio_bytes
        except Exception as e:
            raise TrackExportError(e)

    async def import_track(self, track_path: Path) -> SpotifyTrack:
        """Import track at TRACK_PATH to external library."""
        raise NotImplementedError()  # TODO

    async def update_playlist(self, playlist: SpotifyPlaylist) -> None:
        raise NotImplementedError()  # TODO
