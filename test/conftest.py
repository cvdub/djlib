import logging
import random
import string
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from djlib.config import Config
from djlib.database import Database
from djlib.logging import override_log_level
from djlib.models import (
    RekordboxPlaylist,
    RekordboxTrack,
    SpotifyPlaylist,
    SpotifyTrack,
)
from platformdirs import user_cache_dir


def random_string(length: int) -> str:
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def random_temporary_path(suffix: str) -> Path:
    return Path(tempfile.tempdir) / (random_string(20) + suffix)


@pytest.fixture(scope="session", autouse=True)
def config():
    with (
        patch.object(
            Config,
            "cache_directory",
            new=user_cache_dir("djlib-test", ensure_exists=True),
        ),
        patch.object(Config, "database_file", new=":memory:"),
    ):
        yield


@pytest.fixture(scope="session", autouse=True)
def set_log_level_to_debug():
    with override_log_level(logging.DEBUG):
        yield


@pytest.fixture
async def database():
    async with Database() as database:
        yield database


def random_spotify_id() -> str:
    return random_string(22)


async def _model_factory(model_class, defaults: dict, save=True, **kwargs):
    defaults |= kwargs
    instance = model_class(**defaults)
    if save:
        await instance.save()
    return instance


@pytest.fixture
async def spotify_playlist_factory(database):
    async def _spotify_playlist_factory(save=True, **kwargs) -> SpotifyPlaylist:
        return await _model_factory(
            SpotifyPlaylist,
            {
                "external_id": random_spotify_id(),
                "name": random_string(20),
                "snapshot_id": random_string(32),
            },
            save=save,
            **kwargs,
        )

    return _spotify_playlist_factory


@pytest.fixture
async def spotify_track_factory(database):
    async def _spotify_track_factory(save=True, **kwargs) -> SpotifyTrack:
        return await _model_factory(
            SpotifyTrack,
            {"external_id": random_spotify_id(), "title": random_string(20)},
            save=save,
            **kwargs,
        )

    return _spotify_track_factory


def random_rekordbox_id() -> str:
    return random_string(22)


@pytest.fixture
async def rekordbox_playlist_factory(database):
    async def _rekordbox_playlist_factory(save=True, **kwargs) -> RekordboxPlaylist:
        return await _model_factory(
            RekordboxPlaylist,
            {
                "external_id": random_rekordbox_id(),
                "name": random_string(20),
                "path": random_temporary_path(".mp3"),
            },
            save=save,
            **kwargs,
        )

    return _rekordbox_playlist_factory


@pytest.fixture
async def rekordbox_track_factory(database):
    async def _rekordbox_track_factory(save=True, **kwargs) -> RekordboxTrack:
        return await _model_factory(
            RekordboxTrack,
            {
                "external_id": random_rekordbox_id(),
                "title": random_string(20),
                "path": random_temporary_path(".mp3"),
            },
            save=save,
            **kwargs,
        )

    return _rekordbox_track_factory
