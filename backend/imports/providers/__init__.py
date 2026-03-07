from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imports.models import ImportSource

from .base import ImportSourceProvider


def get_provider(source: "ImportSource") -> ImportSourceProvider:
    """Return the appropriate provider implementation for the given source."""
    from imports.models import ImportSource as IS
    if source.provider_type == IS.PROVIDER_FESTIVALPRO:
        from .festivalpro import FestivalProProvider
        return FestivalProProvider()
    raise NotImplementedError(f"No provider implemented for type: {source.provider_type!r}")
