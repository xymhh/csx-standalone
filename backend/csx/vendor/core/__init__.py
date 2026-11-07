"""Core protocol and data definitions included in the P2 vendor closure."""

from __future__ import annotations

import sys

from csx.vendor.compat import aria2 as _aria2

from .delegation import OwnerDelegator, get_component, resolve_component
from .search import SearchQuery, format_search_label

# transfer.py imports this host-owned optional package; alias its compat shim without
# copying the excluded MoviePilot aria2 implementation into the P2 source closure.
sys.modules[f"{__name__}.aria2"] = _aria2

__all__ = [
    "OwnerDelegator",
    "SearchQuery",
    "format_search_label",
    "get_component",
    "resolve_component",
]
