"""resource.py 领域模型测试。"""

from __future__ import annotations

from csx.domain.resource import (
    BUCKET_ORDER,
    dedup_key,
    idempotency_key,
    quality_bucket,
    score,
)


class TestBucketOrder:
    def test_bucket_order_tuple(self):
        assert BUCKET_ORDER == ("sd", "720p", "1080p", "4k")


class TestQualityBucket:
    def test_none_returns_sd(self):
        assert quality_bucket(None) == "sd"

    def test_empty_string_returns_sd(self):
        assert quality_bucket("") == "sd"

    def test_4k_variants(self):
        assert quality_bucket("4K") == "4k"
        assert quality_bucket("4k") == "4k"
        assert quality_bucket("4K ") == "4k"
        assert quality_bucket(" 4K") == "4k"
        assert quality_bucket(4096) == "4k"
        assert quality_bucket(3840) == "4k"

    def test_2160p_variant(self):
        assert quality_bucket("2160p") == "4k"
        assert quality_bucket("2160P") == "4k"
        assert quality_bucket("2160") == "4k"

    def test_1080p_variants(self):
        assert quality_bucket("1080p") == "1080p"
        assert quality_bucket("1080P") == "1080p"
        assert quality_bucket("1080") == "1080p"
        assert quality_bucket(1920) == "1080p"

    def test_720p_variants(self):
        assert quality_bucket("720p") == "720p"
        assert quality_bucket("720P") == "720p"
        assert quality_bucket("720") == "720p"
        # 1280 高度是 720p，但作为宽度数值是 1280，会被解析为 >=1080 → 1080p
        # 规格说接受分辨率如 "4K"/"2160p" 等，通常指高度
        # 但对于纯数字，我们按值判断
        assert quality_bucket(1280) == "1080p"  # 1280 > 1080

    def test_lower_resolutions(self):
        assert quality_bucket("480p") == "sd"
        assert quality_bucket("360p") == "sd"
        assert quality_bucket(640) == "sd"

    def test_invalid_input(self):
        assert quality_bucket("invalid") == "sd"
        assert quality_bucket("5000p") == "4k"  # 超过 2160 仍是 4k
        assert quality_bucket("abc") == "sd"

    def test_whitespace_handling(self):
        assert quality_bucket("  1080p  ") == "1080p"
        assert quality_bucket("  4K  ") == "4k"


class TestDedupKey:
    def test_basic(self):
        key = dedup_key("provider", "http://example.com/share")
        assert len(key) == 40  # sha1 hex length
        assert key.islower()
        assert all(c in "0123456789abcdef" for c in key)

    def test_provider_case_normalized(self):
        k1 = dedup_key("Provider", "url")
        k2 = dedup_key("PROVIDER", "url")
        k3 = dedup_key("provider", "url")
        assert k1 == k2 == k3

    def test_url_trailing_space_normalized(self):
        k1 = dedup_key("p", "http://x.com/a")
        k2 = dedup_key("p", "http://x.com/a ")
        k3 = dedup_key("p", " http://x.com/a")
        assert k1 == k2 == k3

    def test_consistent_output(self):
        inputs = [("test", "http://example.com/x"), ("provider", "https://share.io/y")]
        for provider, url in inputs:
            k1 = dedup_key(provider, url)
            k2 = dedup_key(provider, url)
            assert k1 == k2


class TestIdempotencyKey:
    def test_format_is_sha1(self):
        key = idempotency_key("p", "u", 1, 2, "1080p")
        assert len(key) == 40
        assert key.islower()

    def test_deterministic(self):
        k1 = idempotency_key("provider", "http://x.com/s", 5, 10, "4k")
        k2 = idempotency_key("provider", "http://x.com/s", 5, 10, "4k")
        assert k1 == k2

    def test_provider_lowercase(self):
        k1 = idempotency_key("ProViDeR", "u", 1, 1, "sd")
        k2 = idempotency_key("provider", "u", 1, 1, "sd")
        assert k1 == k2

    def test_url_stripped_only(self):
        # 只去首尾空白，中间空白保留
        k1 = idempotency_key("p", "a b", 1, 1, "sd")
        k2 = idempotency_key("p", " a b ", 1, 1, "sd")
        assert k1 == k2

    def test_unknown_bucket_normalized_to_sd(self):
        # 规格：bucket 不在 BUCKET_ORDER 里时按 sd 处理
        k1 = idempotency_key("p", "u", 1, 1, "unknown")
        k2 = idempotency_key("p", "u", 1, 1, "sd")
        assert k1 == k2

    def test_known_bucket(self):
        k1 = idempotency_key("p", "u", 1, 1, "720p")
        k2 = idempotency_key("p", "u", 1, 1, "720p")
        assert k1 == k2


class TestScore:
    def test_bucket_rank_monotonicity(self):
        """验证桶权重的单调性：4k > 1080p > 720p > sd"""
        s_sd = score("sd")
        s_720 = score("720p")
        s_1080 = score("1080p")
        s_4k = score("4k")
        assert s_sd < s_720 < s_1080 < s_4k

    def test_subtitle_bonus(self):
        s_no_sub = score("1080p", has_subtitles=False)
        s_with_sub = score("1080p", has_subtitles=True)
        assert s_with_sub - s_no_sub == 5.0

    def test_size_bonus_capped_at_9(self):
        s_small = score("1080p", size_bytes=1e9)  # bonus = 1.0
        s_large = score("1080p", size_bytes=10e9)  # bonus = min(10, 9) = 9
        assert s_large - s_small == 8.0

    def test_size_none_or_negative_as_zero(self):
        s_none = score("1080p", size_bytes=None)
        s_neg = score("1080p", size_bytes=-1)
        s_zero = score("1080p", size_bytes=0)
        assert s_none == s_neg == s_zero

    def test_score_rounding(self):
        # size_bytes=123456789 → bonus ≈ 0.123456789 → round to 2 decimals
        s = score("sd", has_subtitles=True, size_bytes=123456789)
        assert isinstance(s, float)
        # 验证两位小数
        rounded = round(s, 2)
        assert s == rounded

    def test_invalid_bucket_as_sd(self):
        s_unknown = score("unknown_quality")
        s_sd = score("sd")
        assert s_unknown == s_sd

    def test_exact_cap_at_one_gb(self):
        # size_bytes=1e9 → bonus = 1.0
        s = score("sd", size_bytes=1_000_000_000)
        expected = 0 * 100 + 0.0 + 1.0  # bucket_rank + subtitle + size
        assert s == expected

    def test_max_size_bonus(self):
        # size_bytes >= 9e9 → bonus = 9.0
        s = score("sd", size_bytes=9_000_000_000)
        assert s == 0 * 100 + 0.0 + 9.0
