"""失败原因归一化：把冗长的原始异常映射成一行短标签。"""

from __future__ import annotations

# 顺序敏感：先匹配更具体的描述
_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("未命中秒传", "秒传失败", "未命中"), "未命中秒传"),
    (("分享失效", "分享已失效", "分享不存在", "share_invalid"), "分享失效"),
    (("提取码", "password_required", "需要密码"), "需要提取码"),
    (("分享文件列表为空", "分享不可读"), "分享读不到文件"),
    (("未找到 S", "未找到对应", "没有匹配的集"), "分享内无该集"),
    (("未配置", "no account", "account_missing"), "未配置网盘账号"),
    (("整理失败", "organize"), "整理归档失败"),
    (("未生成文件", "部分文件转存失败", "转存未生成"), "转存未落盘"),
    (("空间不足", "capacity", "not enough space"), "网盘空间不足"),
    (("限流", "too many requests", "429", "频率"), "网盘限流"),
    (("超时", "timeout", "timed out"), "网络超时"),
    (("权限", "forbidden", "403", "denied"), "权限不足"),
    (("connection", "网络", "unreachable", "ssl"), "网络错误"),
)

_FALLBACK = "其他失败"


def failure_label(error: str | None) -> str:
    """返回失败短标签；空错误返回空串（表示没有失败原因可展示）。"""
    text = str(error or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    for keywords, label in _RULES:
        if any(keyword.lower() in lowered for keyword in keywords):
            return label
    return _FALLBACK


def failure_detail(error: str | None, limit: int = 300) -> str:
    """原始错误只用于悬停查看，截断到 limit 个字符。"""
    text = str(error or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"
