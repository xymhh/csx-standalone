from types import SimpleNamespace

from csx.application.organize_scan import plan_organize


def test_plan_organize_matches_episodes_and_quality():
    files = [
        SimpleNamespace(file_id="f1", name="庆余年.第二季.S02E01.4k.dv.mkv", path="/inbox/庆余年.第二季.S02E01.4k.dv.mkv", size=2048),
        SimpleNamespace(file_id="f2", name="庆余年.第二季.S02E02.1080p.mkv", path="/inbox/庆余年.第二季.S02E02.1080p.mkv", size=1024),
        SimpleNamespace(file_id="f3", name="未知影视.mp4", path="/inbox/未知影视.mp4", size=500),
        SimpleNamespace(file_id="f4", name="庆余年.S02E01.chs.srt", path="/inbox/庆余年.S02E01.chs.srt", size=10),
    ]

    media_items = [
        SimpleNamespace(id=1, title="庆余年", type="tv", year=2019),
    ]

    plan = plan_organize(files, media_items, library_root="/媒体库")
    matched = plan["matched"]
    unrecognized = plan["unrecognized"]

    assert len(matched) == 2
    assert matched[0]["file_id"] == "f1"
    assert matched[0]["season"] == 2
    assert matched[0]["episode"] == 1
    assert matched[0]["quality_bucket"] == "dv"
    assert "Season 02" in matched[0]["target_path"]
    assert "[DV]" in matched[0]["target_path"]

    assert matched[1]["file_id"] == "f2"
    assert matched[1]["episode"] == 2

    assert len(unrecognized) == 2
    reasons = [u["reason"] for u in unrecognized]
    assert "无法匹配片名或季集" in reasons
    assert "字幕文件随视频整理" in reasons
