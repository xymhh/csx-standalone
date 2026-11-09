"""Translate vendor search definitions into stable application-facing schemas."""

from __future__ import annotations

import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any
from urllib.parse import parse_qs, urlparse

from csx.vendor.search.scanner import SearchSourceRegistry

_ACCOUNT_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_ACCOUNT_CACHE_LOCK = threading.Lock()
_ACCOUNT_CACHE_TTL = 180

_OAUTH_PENDING: dict[str, dict[str, Any]] = {}
_OAUTH_LOCK = threading.Lock()
_OAUTH_TTL = 600


class SearchSourceAdapter:
    """Schema and connectivity boundary for vendor search sources."""

    @staticmethod
    def definitions() -> list[type]:
        return SearchSourceRegistry.get_definitions()

    @classmethod
    def source_ids(cls) -> set[str]:
        return {str(definition.id) for definition in cls.definitions()}

    @staticmethod
    def _merge_value(default: Any, current: Any) -> Any:
        if isinstance(default, dict) and isinstance(current, dict):
            return {
                key: SearchSourceAdapter._merge_value(default.get(key), current.get(key))
                if key in current
                else value
                for key, value in default.items()
            } | {key: value for key, value in current.items() if key not in default}
        return current if current is not None else default

    @classmethod
    def schemas(cls, saved: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        saved = saved or {}
        result = []
        for definition in cls.definitions():
            source_values = saved.get(definition.id, {})
            if not isinstance(source_values, dict):
                source_values = {"enabled": bool(source_values)}
            fields_seen: set[str] = set()
            groups = []
            for group in definition.get_config_groups():
                fields = []
                for spec in group.fields:
                    field = spec.to_dict()
                    key = str(field.get("key") or "")
                    if not key:
                        continue
                    fields_seen.add(key)
                    default = field.get("default")
                    value = cls._merge_value(
                        default,
                        source_values.get(key, saved.get(key, default)),
                    )
                    fields.append(
                        {
                            **field,
                            "default": default,
                            "value": value,
                            "description": field.get("hint", ""),
                        }
                    )
                groups.append({"title": group.title, "fields": fields})
            if "enabled" not in fields_seen:
                enable_field = {
                    "key": "enabled",
                    "label": "启用此搜索源",
                    "type": "switch",
                    "default": True,
                    "value": source_values.get("enabled", True),
                    "description": "控制该搜索源是否参与资源搜索。",
                }
                if groups:
                    groups[0]["fields"].insert(0, enable_field)
                else:
                    groups.append({"title": "基础设置", "fields": [enable_field]})
            result.append(
                {
                    "id": definition.id,
                    "name": definition.name,
                    "order": int(getattr(definition, "order", 100)),
                    "groups": groups,
                }
            )
        return result

    @staticmethod
    def _probe(definition: type, config: dict[str, Any]) -> tuple[bool, str]:
        context = definition.build_test_context(config, {})
        client = definition.create_client(config, context)
        if client is None:
            return False, "请先填写该搜索源所需的连接信息"
        try:
            for method_name in (
                "health",
                "ping",
                "test_connection",
                "check_connection",
                "get_account_info",
            ):
                method = getattr(client, method_name, None)
                if not callable(method):
                    continue
                try:
                    result = method(timeout=10) if method_name in {"health", "ping"} else method()
                except TypeError:
                    result = method()
                if isinstance(result, dict):
                    error = str(result.get("error") or "")
                    status = str(result.get("status") or "").lower()
                    connected = result.get("connected")
                    valid = (
                        not error
                        and status not in {"error", "failed", "fail"}
                        and connected is not False
                    )
                    return valid, error or ("连通正常" if valid else "搜索源未通过连通性检查")
                valid = bool(result)
                return valid, "连通正常" if valid else "搜索源未通过连通性检查"
            return False, "该搜索源未提供主动连通性探针"
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    @classmethod
    def test_source(cls, source_id: str, config: dict[str, Any]) -> dict[str, Any]:
        definition = next((item for item in cls.definitions() if item.id == source_id), None)
        if definition is None:
            raise KeyError(source_id)
        started = time.monotonic()
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(cls._probe, definition, config)
        try:
            valid, message = future.result(timeout=10)
        except TimeoutError:
            future.cancel()
            valid, message = False, "测试超时（10 秒）"
        except Exception as error:
            valid, message = False, str(error) or "搜索源测试失败"
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        return {
            "valid": bool(valid),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "message": message,
        }

    @staticmethod
    def definition(source_id: str) -> type | None:
        return next(
            (item for item in SearchSourceAdapter.definitions() if item.id == source_id), None
        )

    @classmethod
    def _call_with_timeout(cls, func, seconds: float):
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(func)
        try:
            return future.result(timeout=seconds)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    @classmethod
    def _client_for(cls, source_id: str, config: dict[str, Any]):
        definition = cls.definition(source_id)
        if definition is None:
            raise KeyError(source_id)
        context = definition.build_test_context(config, {})
        return definition, definition.create_client(config, context)

    @staticmethod
    def _account_card(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "connected": True,
            "name": str(data.get("name") or data.get("username") or ""),
            "username": str(data.get("username") or ""),
            "email": str(data.get("email") or ""),
            "avatar": str(data.get("avatar") or ""),
            "points": data.get("points"),
            "level": str(data.get("level") or data.get("level_name") or ""),
            "is_vip": data.get("is_vip"),
            "extra": {
                key: value
                for key, value in data.items()
                if key
                in {
                    "upload_count",
                    "favorite_count",
                    "checkin_today",
                    "last_checkin",
                    "user_number",
                    "expire_at",
                }
            },
        }

    @classmethod
    def account_info(
        cls, source_id: str, config: dict[str, Any], *, refresh: bool = False
    ) -> dict[str, Any]:
        now = time.monotonic()
        with _ACCOUNT_CACHE_LOCK:
            cached = _ACCOUNT_CACHE.get(source_id)
            if cached and not refresh and now - cached[0] < _ACCOUNT_CACHE_TTL:
                return cached[1]
            if cached and not refresh:
                return cached[1]
        try:
            _definition, client = cls._client_for(source_id, config)
        except Exception as error:
            return {"connected": False, "error": f"渠道初始化失败：{error}"}
        if client is None:
            return {"connected": False, "error": "请先填写该渠道的连接信息并保存"}

        def _load() -> dict[str, Any]:
            getter = getattr(client, "get_account_info", None)
            if not callable(getter):
                raise RuntimeError("该渠道不提供账户信息")
            return getter()

        try:
            data = cls._call_with_timeout(_load, 10)
            card = cls._account_card(dict(data or {}))
        except TimeoutError:
            card = {"connected": False, "error": "读取账户信息超时"}
        except Exception as error:
            card = {"connected": False, "error": f"账户信息读取失败：{error}"}
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()
        with _ACCOUNT_CACHE_LOCK:
            _ACCOUNT_CACHE[source_id] = (now, card)
        return card

    @classmethod
    def cached_accounts(cls) -> dict[str, dict[str, Any]]:
        with _ACCOUNT_CACHE_LOCK:
            return {key: value[1] for key, value in _ACCOUNT_CACHE.items()}

    @classmethod
    def dynamic_options(cls, scope: str, key: str, config: dict[str, Any]) -> dict[str, Any]:
        definition = cls.definition(scope)
        if definition is None or not hasattr(definition, "get_dynamic_options"):
            raise KeyError(scope)
        options = cls._call_with_timeout(lambda: definition.get_dynamic_options(config, {}), 12)
        if key and isinstance(options, dict):
            values = options.get(key)
            return {
                "status": options.get("status", ""),
                "items": values or [],
                "error": options.get("error", ""),
            }
        return dict(options or {})

    @staticmethod
    def _oauth_values(payload: dict[str, Any]) -> tuple[str, str, str, str]:
        client_id = str(payload.get("client_id") or "").strip()
        redirect_uri = str(payload.get("redirect_uri") or "").strip()
        response_mode = str(payload.get("response_mode") or "redirect").strip().lower()
        requested = [
            value
            for value in str(payload.get("scope") or "query unlock write").split()
            if value in {"query", "unlock", "write"}
        ]
        scopes = list(dict.fromkeys(requested))
        if "query" not in scopes:
            scopes.insert(0, "query")
        if "write" not in scopes:
            scopes.append("write")
        if not client_id:
            raise ValueError("请填写 HDHive OpenAPI Client ID")
        parsed = urlparse(redirect_uri)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.fragment:
            raise ValueError("OAuth Redirect URI 必须是无 fragment 的完整 HTTP/HTTPS 地址")
        if response_mode not in {"redirect", "postmessage"}:
            raise ValueError("仅支持 redirect 或 postmessage 授权回调")
        return client_id, redirect_uri, " ".join(scopes), response_mode

    @classmethod
    def hdhive_oauth_start(cls, payload: dict[str, Any]) -> dict[str, Any]:
        from csx.vendor.search.hdhive import HDHiveOpenAPIClient

        client_id, redirect_uri, scope, response_mode = cls._oauth_values(payload or {})
        state = secrets.token_urlsafe(32)
        client = HDHiveOpenAPIClient(app_secret="", client_id=client_id)
        try:
            authorize_url = client.build_authorize_url(
                redirect_uri=redirect_uri,
                scope=scope,
                state=state,
                response_mode=response_mode,
            )
        finally:
            client.close()
        with _OAUTH_LOCK:
            _OAUTH_PENDING[state] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "response_mode": response_mode,
                "created_at": time.time(),
            }
        return {
            "authorize_url": authorize_url,
            "state": state,
            "response_mode": response_mode,
            "expires_in": _OAUTH_TTL,
        }

    @classmethod
    def hdhive_oauth_exchange(cls, payload: dict[str, Any]) -> dict[str, Any]:
        from csx.vendor.search.hdhive import HDHiveOpenAPIClient, HDHiveOpenAPIError

        payload = dict(payload or {})
        client_id, redirect_uri, _scope, response_mode = cls._oauth_values(payload)
        app_secret = str(payload.get("app_secret") or "").strip()
        if not app_secret:
            raise ValueError("请填写 HDHive OpenAPI 应用 Secret")
        code = str(payload.get("code") or "").strip()
        state = str(payload.get("state") or "").strip()
        callback = str(payload.get("callback") or "").strip()
        if callback:
            parsed = urlparse(callback)
            query = parsed.query if parsed.scheme else callback.lstrip("?")
            values = parse_qs(query, keep_blank_values=True)
            code = str((values.get("code") or [code])[0] or "").strip()
            state = str((values.get("state") or [state])[0] or "").strip()
        if not code or not state:
            raise ValueError("请粘贴包含 code 和 state 的完整回调 URL")
        with _OAUTH_LOCK:
            pending = _OAUTH_PENDING.get(state)
        if not pending or time.time() - float(pending.get("created_at") or 0) > _OAUTH_TTL:
            raise ValueError("授权 state 已失效，请重新打开授权页")
        if (
            pending.get("client_id") != client_id
            or pending.get("redirect_uri") != redirect_uri
            or pending.get("response_mode") != response_mode
        ):
            raise ValueError("授权回调与发起授权时的应用配置不一致")
        client = HDHiveOpenAPIClient(app_secret=app_secret, client_id=client_id)
        try:
            token_data = client.exchange_code(code, redirect_uri)
            warning = ""
            user: dict[str, Any] = {}
            try:
                user = client.get_me().get("data") or {}
            except HDHiveOpenAPIError as error:
                warning = f"Token 已获取，但读取授权用户失败：[{error.code}] {error.message}"
            with _OAUTH_LOCK:
                _OAUTH_PENDING.pop(state, None)
            return {
                "access_token": client.access_token,
                "refresh_token": client.refresh_token,
                "token_expires_at": client.token_expires_at,
                "expires_in": token_data.get("expires_in") or 0,
                "refresh_expires_in": token_data.get("refresh_expires_in") or 0,
                "scope": token_data.get("scope") or pending.get("scope") or "",
                "scopes": token_data.get("scopes") or [],
                "user": user,
                "warning": warning,
            }
        finally:
            client.close()
