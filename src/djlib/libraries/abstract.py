from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional, Self, Type

from ..clients import Client


class Library(ABC):
    """Class for managing a music library."""

    client_class: type[Client] = None

    def __init__(self):
        self._client = self.client_class()

    async def __aenter__(self) -> Self:
        await self._client.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[type[BaseException]],
        exc_tb: Optional[TracebackType],
    ):
        await self._client.close()

    @abstractmethod
    async def refresh(self) -> None:
        """Refresh models with data from client."""
        pass
