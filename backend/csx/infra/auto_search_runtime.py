"""订阅自动搜源的进程内入口（供 scheduler 周期调用）。"""

from __future__ import annotations

from typing import Any

from csx.application import auto_search
from csx.infra.log import logger


def scheduled_auto_search(session_factory) -> dict[str, Any] | None:
    with session_factory() as db:
        config = auto_search.load_settings(db)
        if not config["enabled"]:
            return None
        try:
            result = auto_search.run_round(db)
        except Exception as error:  # 整轮失败不应拖垮调度器
            logger.info(f"[auto_search] 整轮失败：{error}")
            return None
        if result.get("total"):
            logger.info(
                "[auto_search] 本轮 %s 部订阅，候选 %s 个，建任务 %s 个",
                result.get("total"),
                result.get("candidates"),
                result.get("tasks"),
            )
        return result
