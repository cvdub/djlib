from abc import ABC, abstractmethod


class Library(ABC):
    """Class for managing a music library."""

    client_class: = None

    @abstractmethod
    async def refresh(self) -> None:
        """Refresh models with data from client."""
        pass
