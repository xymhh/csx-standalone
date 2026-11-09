"""按后台已配置的搜索渠道执行真实搜索，并把候选归一成前端可用结构。"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.infra.log import logger
from csx.infra.models import Setting
from csx.vendor.compat.schemas import MediaInfo, MediaType
from csx.vendor.core.search import (
    SEARCH_CIRCUIT_BREAKER,
    SearchCapability,
    SearchQuery,
    normalize_search_candidate,
)
from csx.vendor.search.registry import SearchSourceRegistry
from csx.vendor.search.types import (
    resource_type_from_url,
    resource_type_name,
)

#: 单次搜索的整体时间预算（秒）：到点先返回已完成的渠道，其余标记超时。
OVERALL_BUDGET = 15.0
#: 渠道失败后的冷却秒数，避免每次都去撞超时/风控渠道。
FAILURE_COOLDOWN = 300.0
#: 同时执行的渠道数。
MAX_WORKERS = 4
#: 缺省资源类型顺序（与设置页默认值一致）。
_DEFAULT_RESOURCE_TYPES = (
    "115",
    "quark",
    "alipan",
    "uc",
    "tianyi",
    "123",
    "magnet",
    "ed2k",
)

_STORE_LOCK = threading.Lock()
_STORE: dict[str, Any] = {}


class SearchOwnerShim:
    """把扁平配置包装成 vendor 搜索渠道期望的 owner 形态。

    vendor 里的渠道直接读 ``owner._pansou_url``、``owner._hdhive_username`` 这类属性，
    并调用 ``get_data/save_data`` 保存积分类缓存。这里统一按下划线前缀映射配置键，
    未配置的属性返回 ``None``（渠道自己会给出「请先填写…」的提示）。
    """

    def __init__(self, config: dict[str, Any], resource_types: Iterable[str]) -> None:
        self._config = dict(config or {})
        self._resource_type_order_config = tuple(resource_types)
        self._resource_type_order = tuple(resource_types)
        self._cloud_drive_resource_types = tuple(resource_types)
        self.plugin = self
        self._plugin = self
        proxy = str(self._config.get("search_proxy") or "").strip()
        self._search_proxy = proxy or None

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        if name.startswith("_"):
            return self._config.get(name[1:])
        raise AttributeError(name)

    def get_data(self, key: str, default: Any = None) -> Any:
        with _STORE_LOCK:
            return _STORE.get(f"search:{key}", default)

    def save_data(self, key: str, value: Any) -> None:
        with _STORE_LOCK:
            _STORE[f"search:{key}"] = value


def saved_sources(db: Session) -> dict[str, Any]:
    rows = db.scalars(select(Setting).where(Setting.key.like("sources.%"))).all()
    saved: dict[str, Any] = {}
    for row in rows:
        key = row.key.removeprefix("sources.")
        try:
            saved[key] = json.loads(row.value)
        except (TypeError, json.JSONDecodeError):
            saved[key] = row.value
    return saved


def vendor_config(saved: dict[str, Any]) -> dict[str, Any]:
    """合并「定义默认值 ← 已保存值」，未保存时也能用默认地址探测。"""
    from csx.adapters.search.registry import SearchSourceAdapter

    config: dict[str, Any] = {}
    for definition in SearchSourceAdapter.definitions():
        for group in definition.get_config_groups():
            for spec in group.fields:
                if spec.key and spec.default not in (None, "", [], {}):
                    config.setdefault(spec.key, spec.default)
    for source_id, source_values in saved.items():
        if source_id == "global":
            continue
        if isinstance(source_values, dict):
            config.update(source_values)
    global_settings = saved.get("global")
    if isinstance(global_settings, dict):
        proxy = str(global_settings.get("search_proxy") or "").strip()
        if proxy:
            config["search_proxy"] = proxy
    return config


def resource_types_for(saved: dict[str, Any]) -> tuple[str, ...]:
    global_settings = saved.get("global")
    values: Any = None
    if isinstance(global_settings, dict):
        values = global_settings.get("resource_type_order")
    if not isinstance(values, (list, tuple)) or not values:
        return _DEFAULT_RESOURCE_TYPES
    cleaned = []
    for value in values:
        key = str(value or "").strip().lower()
        if key and key not in cleaned:
            cleaned.append(key)
    return tuple(cleaned) or _DEFAULT_RESOURCE_TYPES


def _source_order(saved: dict[str, Any]) -> list[str]:
    global_settings = saved.get("global")
    if not isinstance(global_settings, dict):
        return []
    values = global_settings.get("search_source_order")
    if not isinstance(values, list):
        return []
    order = []
    for value in values:
        key = str(value or "").strip().lower()
        if key and key not in order:
            order.append(key)
    return order


def _ordered_definitions(saved: dict[str, Any]) -> list[type]:
    definitions = [
        definition
        for definition in SearchSourceRegistry.get_definitions()
        if definition.id != "tgchannels"
    ]
    preferred = _source_order(saved)
    if not preferred:
        return definitions
    rank = {source_id: index for index, source_id in enumerate(preferred)}
    return sorted(
        definitions,
        key=lambda definition: (
            rank.get(definition.id, len(rank)),
            int(getattr(definition, "order", 100)),
        ),
    )


def source_catalog(saved: dict[str, Any]) -> list[dict[str, Any]]:
    """后台已注册的搜索渠道 + 启用状态（供前端来源筛选，顺序服从设置页）。"""
    catalog = []
    for definition in _ordered_definitions(saved):
        has_capability = getattr(definition, "has_capability", None)
        if callable(has_capability) and not has_capability("query"):
            continue
        settings = saved.get(definition.id)
        enabled = True
        if isinstance(settings, dict):
            enabled = bool(settings.get("enabled", True))
        elif settings is not None:
            enabled = bool(settings)
        catalog.append(
            {
                "id": definition.id,
                "name": definition.name,
                "icon": getattr(definition, "icon", ""),
                "order": int(getattr(definition, "order", 100)),
                "enabled": enabled,
            }
        )
    return catalog


def _build_search_service(definition: type, config: dict[str, Any], context: dict[str, Any]) -> Any:
    client = definition.create_client(config, context)
    service = definition.create_service(client, config, context)
    provider = definition.create_provider(service, client, config, context)
    if provider is None:
        return None
    return provider.services.get(SearchCapability.RESOURCE_SEARCH)


def _flatten(rows: Any) -> list[dict[str, Any]]:
    if isinstance(rows, dict):
        flattened: list[dict[str, Any]] = []
        for group in rows.values():
            if isinstance(group, list):
                flattened.extend(row for row in group if isinstance(row, dict))
        return flattened
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def _first_url(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        for item in value:
            text = str(item or "").strip()
            if text:
                return text
        return ""
    return str(value or "").strip()


def _all_urls(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item or "").strip() for item in value if str(item or "").strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _format_size(raw: Any, size_text: Any = "") -> tuple[int | None, str]:
    text = str(size_text or "").strip()
    if text:
        return None, text
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, ""
    if value >= 1024 * 1024:
        return value, _human_size(value)
    if 0 < value <= 500:
        # 部分渠道（如 SeedHub）以 GB 为单位给数字，超出上限视为不可信
        return int(value * 1024**3), f"{value} GB"
    return None, ""


def _human_size(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def _is_transferable(url: str) -> bool:
    if not url.lower().startswith(("http://", "https://")):
        return False
    return bool(resource_type_from_url(url))


def _item_key(source_id: str, url: str, title: str) -> str:
    seed = url or title
    digest = hashlib.sha1(f"{source_id}:{seed}".encode()).hexdigest()[:12]
    return f"{source_id}:{digest}"


def _normalize_item(row: dict[str, Any], source_id: str, source_name: str) -> dict[str, Any] | None:
    candidate = normalize_search_candidate(row, source_id)
    title = str(candidate.get("title") or "").strip()
    urls = _all_urls(candidate.get("url"))
    if not urls:
        urls = _all_urls(row.get("share_url") or row.get("magnet") or "")
    url = urls[0] if urls else ""
    if not title and not url:
        return None
    if not title:
        title = str(row.get("name") or row.get("display_name") or "").strip()
    resource_type = str(candidate.get("resource_type") or "").strip().lower()
    if not resource_type or resource_type == "unknown":
        resource_type = resource_type_from_url(url) or resource_type or "unknown"
    size_value, size_text = _format_size(row.get("size"), row.get("size_text"))
    password = str(row.get("password") or candidate.get("password") or "").strip()
    unlock_points = int(candidate.get("unlock_points") or 0)
    needs_unlock = bool(unlock_points and not url)
    transferable = _is_transferable(url)
    if not transferable and resource_type in {"115", "quark", "alipan", "uc", "tianyi", "123"}:
        transferable = _is_transferable(url)
    return {
        "id": _item_key(source_id, url, title),
        "source": source_id,
        "source_name": source_name,
        "title": title,
        "url": url,
        "urls": urls,
        "password": password,
        "resource_type": resource_type,
        "resource_type_name": resource_type_name(resource_type, resource_type),
        "size": size_value,
        "size_text": size_text,
        "update_time": str(
            candidate.get("update_time") or row.get("pubdate") or row.get("update_time") or ""
        ).strip(),
        "description": str(candidate.get("description") or "").strip(),
        "source_url": str(candidate.get("source_url") or row.get("source_url") or "").strip(),
        "media_page_url": str(candidate.get("media_page_url") or "").strip(),
        "fansub": str(row.get("fansub") or "").strip(),
        "needs_unlock": needs_unlock,
        "unlock_points": unlock_points,
        "can_transfer": transferable,
        "duplicate_of": "",
    }


def _run_source(
    definition: type,
    config: dict[str, Any],
    context: dict[str, Any],
    query: SearchQuery,
) -> list[dict[str, Any]]:
    service = _build_search_service(definition, config, context)
    if service is None:
        raise RuntimeError("该渠道未提供搜索能力或缺少必要配置")
    rows = service.search(query)
    return _flatten(rows)


def search_resources(
    db: Session,
    keyword: str,
    media_type: str = "all",
    year: int | None = None,
    season: int | None = None,
    source_ids: Iterable[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    keyword = str(keyword or "").strip()
    if not keyword:
        return {"query": "", "sources": [], "items": [], "total": 0, "elapsed_ms": 0}

    saved = saved_sources(db)
    config = vendor_config(saved)
    resource_types = resource_types_for(saved)
    owner = SearchOwnerShim(config, resource_types)
    context = {
        "owner": owner,
        "storage_owner": owner,
        "resource_types": resource_types,
        "proxy": owner._search_proxy,
    }

    wanted = {str(value).strip().lower() for value in (source_ids or []) if str(value).strip()}
    limit = max(1, min(int(limit or 20), 100))
    normalized_type = str(media_type or "all").strip().lower()
    vendor_type = MediaType.TV if normalized_type == "tv" else MediaType.MOVIE
    query = SearchQuery(
        mediainfo=MediaInfo(title=keyword, year=year),
        media_type=vendor_type,
        season=season if vendor_type == MediaType.TV else None,
        keyword=keyword,
        resource_list_mode=True,
        result_limit=limit,
    )

    statuses: list[dict[str, Any]] = []
    gathered: list[tuple[str, str, dict[str, Any]]] = []
    tasks: list[tuple[type, str]] = []

    for definition in _ordered_definitions(saved):
        has_capability = getattr(definition, "has_capability", None)
        if callable(has_capability) and not has_capability("query"):
            continue
        if wanted and definition.id not in wanted:
            continue
        settings = saved.get(definition.id)
        if isinstance(settings, dict):
            enabled = bool(settings.get("enabled", True))
        elif settings is not None:
            enabled = bool(settings)
        else:
            enabled = True
        if not enabled:
            statuses.append(
                {
                    "id": definition.id,
                    "name": definition.name,
                    "status": "disabled",
                    "count": 0,
                    "message": "未在设置中启用",
                    "elapsed_ms": 0,
                }
            )
            continue
        tasks.append((definition, definition.name))

    started = time.monotonic()
    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    submit_times: dict[Any, float] = {}
    finish_times: dict[Any, float] = {}
    future_map: dict[Any, tuple[type, str]] = {}
    try:
        for definition, name in tasks:
            # 用户点名的渠道不受熔断影响，全量搜索时跳过冷却中的渠道
            if not wanted and not SEARCH_CIRCUIT_BREAKER.can_execute(definition.id):
                remaining = int(SEARCH_CIRCUIT_BREAKER.cooldown_remaining(definition.id))
                statuses.append(
                    {
                        "id": definition.id,
                        "name": name,
                        "status": "skipped",
                        "count": 0,
                        "message": (
                            f"近期失败已暂时跳过，{remaining} 秒后自动重试"
                            f"（{SEARCH_CIRCUIT_BREAKER.get_reason(definition.id) or '连续失败'}）"
                        ),
                        "elapsed_ms": 0,
                    }
                )
                continue
            future = pool.submit(_run_source, definition, config, context, query)
            future_map[future] = (definition, name)
            submit_times[future] = time.monotonic()
            finish_times[future] = 0.0
            future.add_done_callback(
                lambda item, times=finish_times: times.__setitem__(item, time.monotonic())
            )

        done, _pending = wait(future_map, timeout=OVERALL_BUDGET)
        for future, (definition, name) in future_map.items():
            finished = finish_times.get(future) or time.monotonic()
            elapsed_ms = int((finished - submit_times[future]) * 1000)
            if future not in done:
                future.cancel()
                SEARCH_CIRCUIT_BREAKER.record_failure(
                    definition.id,
                    "搜索超时",
                    threshold=2,
                    cooldown_seconds=FAILURE_COOLDOWN,
                )
                statuses.append(
                    {
                        "id": definition.id,
                        "name": name,
                        "status": "timeout",
                        "count": 0,
                        "message": f"超过 {int(OVERALL_BUDGET)} 秒预算，已跳过（结果来自其它渠道）",
                        "elapsed_ms": elapsed_ms,
                    }
                )
                continue
            try:
                rows = future.result()
            except Exception as error:  # 单源失败不影响其它渠道
                message = str(error).strip() or error.__class__.__name__
                logger.info(f"[search] {definition.id} 搜索失败：{message[:160]}")
                SEARCH_CIRCUIT_BREAKER.record_failure(
                    definition.id,
                    message[:120],
                    threshold=2,
                    cooldown_seconds=FAILURE_COOLDOWN,
                )
                statuses.append(
                    {
                        "id": definition.id,
                        "name": name,
                        "status": "error",
                        "count": 0,
                        "message": _friendly_error(message),
                        "elapsed_ms": elapsed_ms,
                    }
                )
                continue
            items = []
            for row in rows[: max(limit * 3, limit)]:
                item = _normalize_item(row, definition.id, name)
                if item:
                    items.append(item)
            for item in items:
                gathered.append((definition.id, name, item))
            if items:
                SEARCH_CIRCUIT_BREAKER.record_success(definition.id)
                statuses.append(
                    {
                        "id": definition.id,
                        "name": name,
                        "status": "ok",
                        "count": len(items),
                        "message": "",
                        "elapsed_ms": elapsed_ms,
                    }
                )
            else:
                SEARCH_CIRCUIT_BREAKER.record_success(definition.id)
                statuses.append(
                    {
                        "id": definition.id,
                        "name": name,
                        "status": "empty",
                        "count": 0,
                        "message": "没有匹配结果",
                        "elapsed_ms": elapsed_ms,
                    }
                )
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    items = _merge_and_sort(keyword, gathered, limit)
    return {
        "query": keyword,
        "sources": statuses,
        "items": items,
        "total": len(items),
        "elapsed_ms": int((time.monotonic() - started) * 1000),
    }


def _friendly_error(message: str) -> str:
    lowered = message.lower()
    for keyword, text in (
        ("登录", "需要登录或凭据失效"),
        ("password", "需要登录或凭据失效"),
        ("未配置", "未填写必要配置"),
        ("请先填写", "未填写必要配置"),
        ("cloudflare", "被 Cloudflare 拦截，需配置搜索代理"),
        ("timeout", "请求超时"),
        ("超时", "请求超时"),
        ("proxy", "代理不可用"),
        ("connection", "连接失败"),
    ):
        if keyword.lower() in lowered:
            return f"{text}（{message[:80]}）"
    return message[:120]


def _merge_and_sort(
    keyword: str, gathered: list[tuple[str, str, dict[str, Any]]], limit: int
) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    needle = keyword.casefold()
    for source_id, _name, item in gathered:
        url = item.get("url") or ""
        dedupe_key = url or f"{source_id}:{item.get('title')}"
        existing = seen.get(dedupe_key)
        if existing is not None:
            existing["duplicate_of"] = existing["duplicate_of"] or item["id"]
            continue
        item["_score"] = _score(item, needle)
        seen[dedupe_key] = item

    ordered = sorted(
        seen.values(),
        key=lambda row: (row["_score"], row.get("update_time") or ""),
        reverse=True,
    )
    for row in ordered:
        row.pop("_score", None)
    return ordered[: max(limit * 4, 40)]


def _score(item: dict[str, Any], needle: str) -> int:
    title = str(item.get("title") or "").casefold()
    if not needle:
        return 0
    if title == needle:
        return 100
    if needle in title:
        return 60
    compact = needle.replace(" ", "")
    if compact and compact in title.replace(" ", ""):
        return 50
    if all(char in title for char in compact):
        return 10
    return 0
