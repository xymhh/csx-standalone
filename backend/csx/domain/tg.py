"""Pure parsers for Telegram media posts and cloud-drive share links."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from csx.domain.naming import parse_episode_from_name

_URL_RE = re.compile(r"https?://[^\s<>\"'`，。；：！？）》】]+", re.IGNORECASE)
_PASSWORD_RE = re.compile(
    r"(?:提取码|访问码|分享码|密码|口令|pwd|pass(?:word)?|code)\s*(?:为|是|[:：=])?\s*([A-Za-z0-9_-]{2,20})",
    re.IGNORECASE,
)
_HOST_PROVIDERS = {
    "115.com": "115",
    "115cdn.com": "115",
    "anxia.com": "115",
    "quark.cn": "quark",
    "alipan.com": "alipan",
    "aliyundrive.com": "alipan",
    "baidu.com": "baidu",
    "189.cn": "tianyi",
    "123pan.com": "123pan",
    "123pan.cn": "123pan",
    "uc.cn": "uc",
    "lanzou.com": "lanzou",
    "lanzoui.com": "lanzou",
    "lanzoux.com": "lanzou",
    "wenshushu.cn": "wenshushu",
}
_TRAILING_URL_CHARS = ".,，。;；:：!?！?)）]】}》、"
_EPISODE_NOISE = re.compile(
    r"(?ix)(?:\bS\d{1,3}\s*E(?:P)?\s*\d{1,4}(?:\s*[-~至]\s*(?:E(?:P)?)?\s*\d{1,4})?\b"
    r"|\bEPISODE\s*\d{1,4}\b|\bEP?\s*\d{1,4}\b"
    r"|\b第\s*\d{1,3}\s*季\s*第\s*\d{1,4}\s*集\b|\b第\s*\d{1,4}\s*集\b)"
)
_QUALITY_NOISE = re.compile(
    r"(?i)\b(?:2160p|1080p|720p|4k|8k|hdr10\+?|hdr|dv|dolby[ ._-]*vision|remux|web[ ._-]?dl|bluray|bdrip|合集|全集|中字|简中|繁中)\b"
)
_PREFIX_TAGS = re.compile(r"^(?:\[[^\]]{1,24}\]|【[^】]{1,24}】|\([^)]{1,24}\))\s*")
_TITLE_PREFIX = re.compile(r"^(?:片名|标题|剧名|title|资源名称)\s*[:：]\s*", re.IGNORECASE)
_META_LINE = re.compile(
    r"^(?:全网独播|持续更新|每日更新|资源分享|剧集分享|点击查看|关注频道)\s*[!！。]*$"
)
_SPACE_RE = re.compile(r"\s+")


def _provider(url: str) -> str | None:
    try:
        host = (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    for suffix, provider in _HOST_PROVIDERS.items():
        if host == suffix or host.endswith(f".{suffix}"):
            return provider
    return None


def _trim_url(url: str) -> str:
    return url.rstrip(_TRAILING_URL_CHARS)


def _password_near(text: str, url_position: int | None) -> str:
    matches = list(_PASSWORD_RE.finditer(text))
    if not matches:
        return ""
    if url_position is None:
        return matches[0].group(1)
    line_start = text.rfind("\n", 0, url_position) + 1
    line_end = text.find("\n", url_position)
    if line_end < 0:
        line_end = len(text)
    same_line = [item for item in matches if line_start <= item.start() < line_end]
    if same_line:
        return min(same_line, key=lambda item: abs(item.start() - url_position)).group(1)
    nearest = min(matches, key=lambda item: abs(item.start() - url_position))
    # Do not associate a distant code from another share in a long channel post.
    if abs(nearest.start() - url_position) > 500:
        return ""
    return nearest.group(1)


def extract_telegram_links(text: str, extra_urls: list[str] | None = None) -> list[dict]:
    """Extract recognized cloud share URLs and nearby access codes from a post."""
    content = str(text or "")
    candidates: list[tuple[str, int | None]] = [
        (_trim_url(match.group(0)), match.start()) for match in _URL_RE.finditer(content)
    ]
    candidates.extend(
        (_trim_url(str(url).strip()), None) for url in extra_urls or [] if str(url).strip()
    )

    links: list[dict] = []
    seen: set[str] = set()
    for url, position in candidates:
        provider = _provider(url)
        if not provider or url in seen:
            continue
        seen.add(url)
        links.append(
            {
                "url": url,
                "provider": provider,
                "password": _password_near(content, position),
            }
        )
    return links


def _title_candidate(text: str) -> str:
    lines = []
    for raw_line in str(text or "").splitlines()[:2]:
        line = _URL_RE.sub(" ", raw_line).strip()
        if not line or _PASSWORD_RE.search(line):
            continue
        line = re.sub(r"^[^\w\u3400-\u9fff《【]+", "", line)
        line = _TITLE_PREFIX.sub("", line)
        line = _PREFIX_TAGS.sub("", line)
        if re.match(r"^(?:[\w\u3400-\u9fff]*(?:网盘|分享|链接|地址))\s*[:：]?$", line):
            continue
        if _META_LINE.match(line):
            continue
        if line:
            lines.append(line)
    return " ".join(lines)


def extract_telegram_title(text: str) -> tuple[str, int | None, int | None]:
    """Return a cleaned title and optional season/episode from the first two lines."""
    candidate = _title_candidate(text)
    season, episode = parse_episode_from_name(candidate)
    title = _EPISODE_NOISE.sub(" ", candidate)
    title = _QUALITY_NOISE.sub(" ", title)
    title = re.sub(r"\[[^\]]*(?:资源|分享|字幕|熟肉|生肉)[^\]]*\]", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"【[^】]*(?:资源|分享|字幕|熟肉|生肉)[^】]*】", " ", title)
    title = re.sub(
        r"(?:提取码|访问码|分享码|密码|口令|网盘链接)\s*[:：]?.*$", " ", title, flags=re.IGNORECASE
    )
    title = title.replace("《", " ").replace("》", " ")
    title = _SPACE_RE.sub(" ", title).strip(" \t-_|:：,，。!！?？·【】[]")
    return title[:200], season, episode
