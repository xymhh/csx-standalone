"""Settings required by the selected vendored utility modules."""

from types import SimpleNamespace

settings = SimpleNamespace(RMT_MEDIAEXT=frozenset({".mkv", ".mp4", ".avi", ".mov", ".ts"}))
