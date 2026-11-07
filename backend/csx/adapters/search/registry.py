"""Translate vendor search definitions into stable application-facing schemas."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any

from csx.vendor.search.scanner import SearchSourceRegistry


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
