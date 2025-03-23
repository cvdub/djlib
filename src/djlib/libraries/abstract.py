from abc import ABC, abstractmethod

from ..clients import Client


class Library(ABC):
    """Class for managing a music library."""

    client_class: type[Client] = None

    @abstractmethod
    async def refresh(self) -> None:
        """Refresh models with data from client."""
        pass
