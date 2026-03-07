from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imports.models import ImportSource


class ImportSourceProvider(ABC):
    """Abstract base for all import source providers."""

    @abstractmethod
    def fetch(self, source: "ImportSource") -> str:
        """
        Fetch raw JSON text from the external source.
        Raises ProviderLoginError or ProviderFetchError on failure.
        """

    @abstractmethod
    def requires_event(self) -> bool:
        """Return True if this provider requires an event to be linked."""
