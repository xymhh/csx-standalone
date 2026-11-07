"""任务域模型：状态机、超时重试、失败处理。"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum


class TaskState(StrEnum):
    """任务状态。"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRY_WAIT = "retry_wait"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class InvalidTransition(ValueError):
    """非法的状态迁移。"""

    pass


# 定义允许迁移的表（必须完全一致）
ALLOWED_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.QUEUED: frozenset({TaskState.RUNNING, TaskState.CANCELLED}),
    TaskState.RUNNING: frozenset(
        {
            TaskState.SUCCEEDED,
            TaskState.RETRY_WAIT,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }
    ),
    TaskState.RETRY_WAIT: frozenset(
        {
            TaskState.RUNNING,
            TaskState.QUEUED,
            TaskState.CANCELLED,
            TaskState.DEAD_LETTER,
        }
    ),
    TaskState.FAILED: frozenset(
        {
            TaskState.RETRY_WAIT,
            TaskState.DEAD_LETTER,
            TaskState.CANCELLED,
        }
    ),
    TaskState.DEAD_LETTER: frozenset({TaskState.QUEUED}),
    TaskState.SUCCEEDED: frozenset(),  # 终态
    TaskState.CANCELLED: frozenset(),  # 终态
}


def can_transition(src: TaskState, dst: TaskState) -> bool:
    """判断是否允许从 src 迁移到 dst。"""
    allowed = ALLOWED_TRANSITIONS.get(src)
    if allowed is None:
        return False
    return dst in allowed


def assert_transition(src: TaskState, dst: TaskState) -> None:
    """如果非法则抛 InvalidTransition。"""
    if not can_transition(src, dst):
        raise InvalidTransition(f"Cannot transition from {src} to {dst}")


def backoff_seconds(attempt: int) -> int:
    """计算退避秒数。attempt <= 0 按 1 处理。"""
    if attempt <= 1:
        return 60
    # 60 * 2**(attempt-1)，封顶 1800
    value = 60 * (2 ** (attempt - 1))
    return min(value, 1800)


def next_retry_at(now: datetime, attempt: int) -> datetime:
    """计算下次重试时间。输出与输入同类型（带 tz 或 naive）。"""
    delta = timedelta(seconds=backoff_seconds(attempt))
    return now + delta


def on_failure(state: TaskState, attempt: int, max_attempts: int = 3) -> tuple[TaskState, int]:
    """处理失败：返回 (新状态，新 attempt)。"""
    new_attempt = attempt + 1
    if new_attempt >= max_attempts:
        return (TaskState.DEAD_LETTER, new_attempt)
    else:
        return (TaskState.RETRY_WAIT, new_attempt)
