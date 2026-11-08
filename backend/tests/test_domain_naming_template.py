from __future__ import annotations

import pytest

from csx.application.naming import (
    NamingError,
    build_context,
    render_relative_path,
    select_template,
    split_relative_path,
)
from csx.domain.naming import (
    DEFAULT_MOVIE_TEMPLATE,
    DEFAULT_TV_TEMPLATE,
    normalize_relative_path,
)


def _tv(**overrides):
    values = {
        "title": "示例剧集",
        "year": 2024,
        "media_type": "tv",
        "season": 1,
        "episode": 1,
        "extension": "mkv",
        "quality_bucket": "4k",
    }
    values.update(overrides)
    return build_context(**values)


def _movie(**overrides):
    values = {
        "title": "示例电影",
        "year": 2024,
        "media_type": "movie",
        "extension": "mkv",
        "quality_bucket": "1080p",
    }
    values.update(overrides)
    return build_context(**values)


def test_default_movie_template_matches_moviepilot_shape():
    relative = render_relative_path(DEFAULT_MOVIE_TEMPLATE, _movie())
    assert relative == "示例电影 (2024)/示例电影 (2024) - 1080p.mkv"
    assert split_relative_path(relative) == ("示例电影 (2024)", "示例电影 (2024) - 1080p.mkv")


def test_default_tv_template_matches_moviepilot_shape():
    relative = render_relative_path(DEFAULT_TV_TEMPLATE, _tv())
    assert relative == "示例剧集 (2024)/Season 1/示例剧集 - S01E01 - 第 1 集.mkv"


def test_missing_year_leaves_no_empty_parentheses():
    relative = render_relative_path(DEFAULT_MOVIE_TEMPLATE, _movie(year=None))
    assert relative == "示例电影/示例电影 - 1080p.mkv"


def test_unknown_variable_renders_empty_instead_of_breaking():
    context = _tv()
    relative = render_relative_path("{{title}}/{{title}}{{en_title}}{{fileExt}}", context)
    assert relative == "示例剧集/示例剧集.mkv"


def test_template_without_directory_is_rejected():
    with pytest.raises(NamingError):
        render_relative_path("{{title}}{{fileExt}}", _movie())


def test_parent_directory_traversal_is_rejected():
    with pytest.raises(ValueError):
        normalize_relative_path("../etc/passwd")
    with pytest.raises(ValueError):
        render_relative_path("{{title}}/../{{title}}{{fileExt}}", _movie())


def test_illegal_characters_are_cleaned_per_segment():
    relative = render_relative_path("{{title}}/{{title}}{{fileExt}}", _movie(title='A/B: C*?"<>|'))
    assert relative == "A B C/A B C.mkv"


def test_syntax_error_reports_user_facing_message():
    with pytest.raises(NamingError) as error:
        render_relative_path("{{title}", _movie())
    assert "模板语法错误" in str(error.value)


def test_empty_title_is_rejected():
    with pytest.raises(NamingError):
        render_relative_path(DEFAULT_MOVIE_TEMPLATE, _movie(title="   "))


def test_select_template_prefers_movie_and_falls_back_for_variety():
    naming = {"movie": "M", "tv": "T", "variety": ""}
    assert select_template(naming, "movie") == "M"
    assert select_template(naming, "tv") == "T"
    assert select_template(naming, "tv", "variety") == "T"
    assert select_template({}, "tv") == DEFAULT_TV_TEMPLATE


def test_video_format_mapping():
    assert _tv(quality_bucket="4k")["videoFormat"] == "2160p"
    assert _movie(quality_bucket="sd")["videoFormat"] == ""
    assert _movie(quality_bucket="720p")["videoFormat"] == "720p"
