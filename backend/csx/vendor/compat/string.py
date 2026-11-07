"""String formatting functions used by the original MoviePilot integrations."""

from __future__ import annotations

import re


class StringUtils:
    @staticmethod
    def format_size(size: int | float) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
            if value < 1024 or unit == "PB":
                digits = 0 if value >= 100 or unit == "B" else 1
                return f"{value:.{digits}f} {unit}"
            value /= 1024
        return "0 B"

    @classmethod
    def str_filesize(cls, size: int | float) -> str:
        return cls.format_size(size)

    @staticmethod
    def num_filesize(value: str | int | float | None) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value or "").strip().replace(",", "")
        match = re.fullmatch(r"([\d.]+)\s*(B|KB|K|MB|M|GB|G|TB|T)?", text, re.I)
        if not match:
            return 0
        amount = float(match.group(1))
        unit = (match.group(2) or "B").upper()
        power = {"B": 0, "K": 1, "KB": 1, "M": 2, "MB": 2, "G": 3, "GB": 3, "T": 4, "TB": 4}[unit]
        return int(amount * 1024**power)
