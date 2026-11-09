"""通知消息模板：默认模板与渲染。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from jinja2 import ChainableUndefined
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

_ENV = SandboxedEnvironment(undefined=ChainableUndefined, autoescape=False)

EVENTS = ("transfer_success", "upgrade_success", "task_dead_letter")

EVENT_TITLES = {
    "transfer_success": "转存成功",
    "upgrade_success": "洗版成功",
    "task_dead_letter": "转存失败",
}

DEFAULT_TEMPLATES: dict[str, str] = {
    "transfer_success": (
        "✅ 转存成功\n"
        "────────────────\n"
        "🎬 {{ title }}{% if season %}  S{{ '%02d'|format(season|int) }}"
        "E{{ '%02d'|format(episode|int) }}{% endif %}"
        "\n"
        "{% if quality %}💎 画质：{{ quality }}\n{% endif %}"
        "{% if duration %}⏱ 时长：{{ duration }}\n{% endif %}"
        "🕒 {{ now }}"
    ),
    "upgrade_success": (
        "🔄 洗版成功\n"
        "────────────────\n"
        "🎬 {{ title }}{% if season %}  S{{ '%02d'|format(season|int) }}"
        "E{{ '%02d'|format(episode|int) }}{% endif %}"
        "\n"
        "{% if from_quality %}📉 原画质：{{ from_quality }}\n{% endif %}"
        "{% if to_quality %}📈 新画质：{{ to_quality }}\n{% endif %}"
        "🕒 {{ now }}"
    ),
    "task_dead_letter": (
        "❌ 转存失败\n"
        "────────────────\n"
        "{% if title %}🎬 {{ title }}\n{% endif %}"
        "📄 原因：{{ error }}\n"
        "{% if share_url %}🔗 分享：{{ share_url }}\n{% endif %}"
        "🕒 {{ now }}"
    ),
}

# 模板可用的变量说明，供前端展示
TEMPLATE_VARIABLES: dict[str, list[str]] = {
    "transfer_success": [
        "title",
        "season",
        "episode",
        "quality",
        "duration",
        "now",
    ],
    "upgrade_success": [
        "title",
        "season",
        "episode",
        "from_quality",
        "to_quality",
        "now",
    ],
    "task_dead_letter": ["title", "error", "share_url", "now"],
}


def normalize_templates(raw: Any) -> dict[str, str]:
    """合并用户模板与默认模板，空值或非字符串一律回退默认。"""
    merged = dict(DEFAULT_TEMPLATES)
    if isinstance(raw, dict):
        for event, template in raw.items():
            if event not in DEFAULT_TEMPLATES:
                continue
            text = str(template or "").strip()
            if text:
                merged[event] = text
    return merged


def render_template(template: str, payload: dict[str, Any]) -> str:
    context = dict(payload)
    context.setdefault("now", datetime.now().strftime("%Y-%m-%d %H:%M"))
    try:
        return _ENV.from_string(template).render(**context).strip()
    except Exception as error:
        logger.warning("通知模板渲染失败，改用默认模板：%s", error)
        return ""


def render_event(
    templates: Any, event: str, payload: dict[str, Any]
) -> str:
    """渲染某事件的通知文本；模板异常时回退默认模板，仍失败则回退摘要。"""
    resolved = normalize_templates(templates)
    text = render_template(resolved.get(event, ""), payload)
    if text:
        return text
    fallback = render_template(DEFAULT_TEMPLATES.get(event, ""), payload)
    if fallback:
        return fallback
    lines = [event]
    lines.extend(
        f"{key}: {value}" for key, value in payload.items() if key != "text" and value not in (None, "")
    )
    return "\n".join(lines)
