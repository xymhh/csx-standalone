"""Selected utilities re-exported for the vendored P2 dependency closure."""

from .file_parser import MediaFileParser
from .magnet import parse_magnet_metadata

__all__ = ["MediaFileParser", "parse_magnet_metadata"]
