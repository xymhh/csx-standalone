"""资源领域模型：质量桶、去重键、评分。"""

from __future__ import annotations

import hashlib

BUCKET_ORDER: tuple[str, ...] = ("sd", "720p", "1080p", "4k")


def quality_bucket(resolution: str | int | None) -> str:
    """根据分辨率返回质量桶。"""
    if resolution is None:
        return "sd"

    # 规范化：先去空格，转小写
    res_str = str(resolution).strip().lower()
    if not res_str:
        return "sd"

    # 特殊字符串处理（如 "4k", "1080p", "720p" 等）
    if res_str == "4k":
        return "4k"
    if res_str == "2160p":
        return "4k"

    # 尝试解析为数字
    try:
        # 去掉可能的 'p' 后缀
        numeric_part = res_str.rstrip("p")
        numeric_value = int(numeric_part)
    except (ValueError, AttributeError):
        return "sd"

    if numeric_value >= 2160:
        return "4k"
    elif numeric_value >= 1080:
        return "1080p"
    elif numeric_value >= 720:
        return "720p"
    else:
        return "sd"


def _normalize_provider(provider: str) -> str:
    """规范化 provider：strip + lower。"""
    return provider.strip().lower()


def _normalize_share_url(share_url: str) -> str:
    """规范化 share_url：只去首尾空白。"""
    return share_url.strip()


def dedup_key(provider: str, share_url: str) -> str:
    """生成去重键（provider + share_url 的 sha1）。"""
    norm_provider = _normalize_provider(provider)
    norm_url = _normalize_share_url(share_url)
    text = f"{norm_provider}:{norm_url}"
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def idempotency_key(
    provider: str,
    share_url: str,
    season: int,
    episode: int,
    bucket: str,
) -> str:
    """生成幂等键。"""
    norm_provider = _normalize_provider(provider)
    norm_url = _normalize_share_url(share_url)
    # bucket 规范化检查
    effective_bucket = bucket if bucket in BUCKET_ORDER else "sd"
    text = f"{norm_provider}:{norm_url}:{season}:{episode}:{effective_bucket}"
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def score(
    bucket: str,
    *,
    has_subtitles: bool = False,
    size_bytes: int | None = None,
) -> float:
    """计算资源评分。"""
    # bucket 规范化
    effective_bucket = bucket if bucket in BUCKET_ORDER else "sd"

    # bucket 权重
    bucket_rank = BUCKET_ORDER.index(effective_bucket) * 100

    # 字幕加分
    subtitle_bonus = 5.0 if has_subtitles else 0.0

    # 大小加分（上限 9.0）
    size_bonus = 0.0
    if size_bytes is not None and size_bytes > 0:
        size_bonus = min(size_bytes / 1e9, 9.0)

    return round(bucket_rank + subtitle_bonus + size_bonus, 2)
