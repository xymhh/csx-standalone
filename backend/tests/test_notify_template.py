from __future__ import annotations

from csx.application.notify_template import (
    DEFAULT_TEMPLATES,
    normalize_templates,
    render_event,
    render_template,
)


def test_default_template_renders_card_layout():
    text = render_event(
        None,
        "transfer_success",
        {"title": "奥德赛", "season": 1, "episode": 2, "quality": "4k", "duration": "2h"},
    )
    assert "转存成功" in text
    assert "奥德赛" in text
    assert "S01E02" in text
    assert "画质：4k" in text


def test_movie_template_omits_episode_line():
    text = render_event(None, "transfer_success", {"title": "奥德赛 (2026)", "quality": "hd"})
    assert "S01E" not in text
    assert "奥德赛 (2026)" in text


def test_custom_template_wins():
    text = render_event(
        {"task_dead_letter": "挂了：{{ error }}"},
        "task_dead_letter",
        {"error": "分享失效"},
    )
    assert text == "挂了：分享失效"


def test_blank_template_falls_back_to_default():
    text = render_event({"transfer_success": "   "}, "transfer_success", {"title": "X"})
    assert text == render_event(None, "transfer_success", {"title": "X"})


def test_broken_template_falls_back_to_default():
    text = render_event({"transfer_success": "{{ title "}, "transfer_success", {"title": "X"})
    assert "转存成功" in text


def test_missing_variables_do_not_raise():
    text = render_template(DEFAULT_TEMPLATES["upgrade_success"], {"title": "X"})
    assert "洗版成功" in text


def test_normalize_templates_keeps_only_known_events():
    merged = normalize_templates({"transfer_success": "hi", "unknown": "x", "upgrade_success": ""})
    assert merged["transfer_success"] == "hi"
    assert merged["upgrade_success"] == DEFAULT_TEMPLATES["upgrade_success"]
    assert "unknown" not in merged


def test_unknown_event_renders_key_value_fallback():
    text = render_event(None, "custom_event", {"a": 1})
    assert "custom_event" in text
    assert "a: 1" in text
