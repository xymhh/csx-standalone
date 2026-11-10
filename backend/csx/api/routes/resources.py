"""兼容垫片：原 resources.py 已按域拆分，本模块仅转发导出以免旧导入失效。

拆分去向：
- subscriptions.py —— 订阅与候选资源
- transfer.py —— 转存任务与历史
- library.py —— 追剧进度与媒体库
- platform.py —— 设置、网盘账号、系统自检与事件流
- resource_common.py —— 共享小工具（_raise/_page）

新代码请直接从各域模块导入，不要再依赖本垫片。
"""

from csx.api.routes.library import library, progress
from csx.api.routes.platform import accounts, doctor, event_stream, events, settings_api
from csx.api.routes.subscriptions import candidates, subscriptions
from csx.api.routes.transfer import history, tasks

__all__ = [
    "accounts",
    "candidates",
    "doctor",
    "event_stream",
    "events",
    "history",
    "library",
    "progress",
    "settings_api",
    "subscriptions",
    "tasks",
]
