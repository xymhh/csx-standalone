"""各搜索渠道的真实连通性探测。

泛型探针只会调用 `health/ping/get_account_info`，对公开站点（Mikan、SeedHub 等）
和缺少 `create_client` 的定义（Dian115、HDHaven）无法判断，会误报「未提供探针」。
这里按渠道补一到两次最小真实请求：要么登录取账户信息，要么打一次搜索。
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from typing import Any

ProbeResult = tuple[bool, str]

KEYWORD_CN = "三体"
KEYWORD_EN = "test"


def _text(config: dict[str, Any], key: str, default: str = "") -> str:
    value = config.get(key, default)
    if value is None:
        return default
    return str(value).strip()


def _number(config: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(config.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def _proxy(config: dict[str, Any]) -> str | None:
    value = str(config.get("search_proxy") or "").strip()
    return value or None


def _proxies(config: dict[str, Any]) -> dict[str, str] | None:
    value = _proxy(config)
    return {"http": value, "https": value} if value else None


def _close(client: Any) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        with contextlib.suppress(Exception):
            close()


def _error(prefix: str, error: Exception) -> ProbeResult:
    message = str(error).strip() or error.__class__.__name__
    return False, f"{prefix}：{message[:160]}"


def _result_message(count: int) -> str:
    return f"连通正常（返回 {count} 条结果）"


def _probe_dian115(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.dian115.client import Dian115Client

    email = _text(config, "dian115_email")
    password = _text(config, "dian115_password")
    if not email or not password:
        return False, "请先填写 Dian115 的登录邮箱与密码"
    client = Dian115Client(
        email=email,
        password=password,
        base_url=_text(config, "dian115_base_url", "https://m.dian115.com"),
        proxy=_proxy(config),
        request_interval=_number(config, "dian115_request_interval", 1.0),
        unlocks_per_minute=int(_number(config, "dian115_unlocks_per_minute", 6)),
        timeout=int(_number(config, "dian115_timeout", 30)),
    )
    try:
        data = client.get_account_info() or {}
        name = str(data.get("name") or data.get("username") or email)
        return True, f"登录正常：{name}"
    except Exception as error:
        return _error("Dian115 登录失败", error)
    finally:
        _close(client)


def _probe_hdhaven(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.hdhaven.client import HDHavenClient

    username = _text(config, "hdhaven_username")
    password = _text(config, "hdhaven_password")
    if not username or not password:
        return False, "请先填写 HDHaven 的用户名与密码"
    client = HDHavenClient(
        username=username,
        password=password,
        base_url=_text(config, "hdhaven_base_url", "https://hdhaven.com"),
        proxy=_proxy(config),
        request_interval=_number(config, "hdhaven_request_interval", 2.0),
    )
    try:
        data = client.get_account_info() or {}
        name = str(data.get("name") or data.get("username") or username)
        return True, f"登录正常：{name}"
    except Exception as error:
        return _error("HDHaven 登录失败", error)
    finally:
        _close(client)


def _probe_hdhive(config: dict[str, Any]) -> ProbeResult:
    import requests

    base_url = _text(config, "hdhive_base_url", "https://re0.me").rstrip("/")
    try:
        response = requests.get(
            f"{base_url}/api/search",
            params={"keyword": KEYWORD_CN},
            timeout=12,
            proxies=_proxies(config),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
    except Exception as error:
        return _error("HDHive 请求失败", error)
    if response.status_code in {401, 403}:
        return False, (
            f"HDHive 拒绝访问（HTTP {response.status_code}），"
            "通常是 Cloudflare 拦截了服务器出口 IP，可稍后再试或更换镜像地址"
        )
    if response.status_code >= 400:
        return False, f"HDHive 返回 HTTP {response.status_code}"
    return True, "连通正常（站点可访问）"


def _probe_mikan(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.mikan.client import MikanClient

    client = MikanClient(
        base_url=_text(config, "mikan_base_url", "https://mikanani.me"),
        timeout=int(min(_number(config, "mikan_timeout", 30), 30)),
        interval=_number(config, "mikan_request_interval", 2.0),
        proxy=_proxy(config),
    )
    try:
        rows = client.search_html(KEYWORD_CN) or []
        return True, _result_message(len(rows))
    except Exception as error:
        return _error("Mikan 请求失败", error)


def _probe_animegarden(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.animegarden.client import AnimeGardenClient

    client = AnimeGardenClient(
        base_url=_text(config, "animegarden_base_url", "https://api.animes.garden").rstrip("/"),
        timeout=int(min(_number(config, "animegarden_timeout", 30), 30)),
        interval=_number(config, "animegarden_request_interval", 1.0),
        proxy=_proxy(config),
    )
    try:
        rows = client.search(keyword=KEYWORD_CN, page_size=10) or []
        return True, _result_message(len(rows))
    except Exception as error:
        return _error("AnimeGarden 请求失败", error)


def _probe_seedhub(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.seedhub.client import SeedHubClient

    client = SeedHubClient(
        base_url=_text(config, "seedhub_base_url", "https://sidhub.cc"),
        proxy=_proxy(config),
        request_timeout=int(min(_number(config, "seedhub_timeout", 30), 30)),
        request_interval=_number(config, "seedhub_request_interval", 1.0),
    )
    try:
        rows = client.search_candidates(KEYWORD_CN) or []
        return True, _result_message(len(rows))
    except Exception as error:
        return _error("SeedHub 请求失败", error)


def _probe_piratebay(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.piratebay.client import PirateBayClient

    client = PirateBayClient(
        base_url=_text(config, "piratebay_base_url", "https://apibay.org"),
        proxy=_proxy(config),
        timeout=int(min(_number(config, "piratebay_timeout", 20), 30)),
        request_interval=_number(config, "piratebay_request_interval", 1.0),
    )
    try:
        rows = client.search(KEYWORD_EN) or []
        return True, _result_message(len(rows))
    except Exception as error:
        return _error("海盗湾 API 请求失败", error)


def _probe_pianku(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.pianku.client import PiankuClient

    client = PiankuClient(
        base_url=_text(config, "pianku_base_url", "https://4k.pianku.online"),
        proxy=_proxy(config),
        timeout=int(min(_number(config, "pianku_timeout", 30), 30)),
        request_interval=_number(config, "pianku_request_interval", 1.5),
    )
    try:
        rows = client.search_titles(KEYWORD_CN) or []
        return True, _result_message(len(rows))
    except Exception as error:
        return _error("片库请求失败", error)


def _probe_uindex(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.uindex.client import UIndexClient

    client = UIndexClient(
        base_url=_text(config, "uindex_base_url", "https://uindex.org"),
        proxy=_proxy(config),
        timeout=int(min(_number(config, "uindex_timeout", 20), 30)),
        request_interval=_number(config, "uindex_request_interval", 1.0),
    )
    try:
        rows = client.search(KEYWORD_EN) or []
        return True, _result_message(len(rows))
    except Exception as error:
        message = str(error)
        if "CloakBrowser" in message or "Cloudflare" in message:
            return False, (
                "UIndex 需要浏览器通过 Cloudflare 验证，当前环境未授权浏览器引擎；"
                "填写「搜索代理」后重试，或改用其它渠道"
            )
        return _error("UIndex 请求失败", error)


def _probe_online_docs(config: dict[str, Any]) -> ProbeResult:
    from csx.vendor.search.online_docs.client import OnlineDocumentClient

    documents = config.get("online_docs") or []
    urls = [
        str(doc.get("url") or "").strip()
        for doc in documents
        if isinstance(doc, dict) and str(doc.get("url") or "").strip()
    ]
    if not urls:
        return False, "请先添加至少一个在线文档地址"
    client = OnlineDocumentClient(documents=documents, timeout=20, proxy=_proxy(config))
    try:
        result = client.read(urls[0]) or {}
        entries = result.get("entries") or result.get("items") or []
        return True, f"文档可读取（解析出 {len(entries)} 条资源）"
    except Exception as error:
        return _error("在线文档读取失败", error)


def _probe_tgchannels(config: dict[str, Any]) -> ProbeResult:
    return False, "频道监控不提供连通测试，请到「频道监控」页查看 TG 会话与频道状态"


def _probe_with_client(
    site: str, source_id: str, username_key: str, password_key: str
) -> Callable[[dict[str, Any]], ProbeResult]:
    def _probe(config: dict[str, Any]) -> ProbeResult:
        if not _text(config, username_key) or not _text(config, password_key):
            return False, f"请先填写 {site} 的账号与密码"
        from csx.vendor.search.scanner import SearchSourceRegistry

        definition = next(
            (item for item in SearchSourceRegistry.get_definitions() if item.id == source_id),
            None,
        )
        if definition is None:
            return False, f"{site} 定义缺失"
        client = None
        try:
            client = definition.create_client(config, definition.build_test_context(config, {}))
            if client is None:
                return False, f"请先填写 {site} 的账号与密码"
            getter = getattr(client, "get_account_info", None)
            if not callable(getter):
                return True, "连通正常（渠道已初始化）"
            data = getter() or {}
            name = str(data.get("name") or data.get("username") or "")
            return True, f"登录正常：{name}" if name else "登录正常"
        except Exception as error:
            return _error(f"{site} 登录失败", error)
        finally:
            _close(client)

    return _probe


PROBES: dict[str, Callable[[dict[str, Any]], ProbeResult]] = {
    "hdhive": _probe_hdhive,
    "hdhaven": _probe_hdhaven,
    "dian115": _probe_dian115,
    "mikan": _probe_mikan,
    "animegarden": _probe_animegarden,
    "seedhub": _probe_seedhub,
    "piratebay": _probe_piratebay,
    "pianku": _probe_pianku,
    "uindex": _probe_uindex,
    "online_docs": _probe_online_docs,
    "tgchannels": _probe_tgchannels,
    "juying": _probe_with_client("聚影", "juying", "juying_username", "juying_password"),
    "woniu": _probe_with_client("蜗牛", "woniu", "woniu_username", "woniu_password"),
    "pinglian": _probe_with_client("盘链", "pinglian", "pinglian_username", "pinglian_password"),
}


def has_probe(source_id: str) -> bool:
    return source_id in PROBES


def probe(source_id: str, config: dict[str, Any]) -> ProbeResult:
    started = time.monotonic()
    handler = PROBES.get(source_id)
    if handler is None:
        return False, "该渠道暂不支持连通测试"
    ok, message = handler(config or {})
    elapsed = int((time.monotonic() - started) * 1000)
    return ok, f"{message}（{elapsed} ms）" if elapsed > 2000 else message
