from csx.domain.tg import extract_telegram_links, extract_telegram_title


def test_extracts_quark_and_115_links_with_adjacent_passwords():
    text = """《漫长的季节》 S01E02 1080p WEB-DL
夸克：https://pan.quark.cn/s/abc123，提取码：Qwer
115网盘 https://115.com/s/sw4abc. 密码: 1234
"""
    links = extract_telegram_links(text)
    assert links == [
        {"url": "https://pan.quark.cn/s/abc123", "provider": "quark", "password": "Qwer"},
        {
            "url": "https://115.com/s/sw4abc",
            "provider": "115",
            "password": "1234",
        },
    ]


def test_extracts_other_cloud_providers_and_external_urls():
    text = (
        "资源标题\n访问码 abcd\nhttps://www.alipan.com/s/ali-id!\nhttps://pan.baidu.com/s/baidu-id"
    )
    links = extract_telegram_links(text, ["https://drive.uc.cn/s/uc-id", "https://example.com/no"])
    assert [(link["provider"], link["password"]) for link in links] == [
        ("alipan", "abcd"),
        ("baidu", "abcd"),
        ("uc", "abcd"),
    ]
    assert len(links) == 3


def test_deduplicates_urls_and_ignores_unrecognized_hosts():
    url = "https://pan.quark.cn/s/shared"
    links = extract_telegram_links(f"{url} {url}. https://example.com/share")
    assert links == [{"url": url, "provider": "quark", "password": ""}]


def test_extracts_title_and_episode_from_tagged_first_line():
    assert extract_telegram_title("🎬【每日更新】《苍兰诀》 S02E03 1080p WEB-DL\n提取码: abcd") == (
        "苍兰诀",
        2,
        3,
    )


def test_extracts_chinese_season_episode_and_uses_second_title_line():
    assert extract_telegram_title("【剧集分享】\n长相思 第2季 第05集 [HDR]") == (
        "长相思",
        2,
        5,
    )


def test_link_label_on_second_line_does_not_pollute_title():
    assert extract_telegram_title("孤独摇滚 S01E02\n夸克网盘：https://pan.quark.cn/s/abc") == (
        "孤独摇滚",
        1,
        2,
    )


def test_title_without_episode_and_empty_message_are_safe():
    assert extract_telegram_title("片名：繁花 (2023)\n全网独播") == ("繁花 (2023)", None, None)
    assert extract_telegram_title("") == ("", None, None)
