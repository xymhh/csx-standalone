"""Idempotent transfer orchestration with explicit task state transitions."""

from __future__ import annotations

import posixpath
import threading
import time
from contextlib import contextmanager
from datetime import date

from csx.application.organize import organize_file
from csx.domain.naming import parse_episode_from_name
from csx.domain.resource import idempotency_key
from csx.domain.task import TaskState, on_failure

_GLOBAL = threading.BoundedSemaphore(8)
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
_BUCKETS: dict[str, tuple[float, float]] = {}
_BUCKETS_GUARD = threading.Lock()


@contextmanager
def _serialize(key: str):
    with _LOCKS_GUARD:
        lock = _LOCKS.setdefault(key, threading.Lock())
    with lock, _GLOBAL:
        yield


def _take_token(provider: str) -> None:
    rate = 4 if provider == "115" else 8
    while True:
        now = time.monotonic()
        with _BUCKETS_GUARD:
            tokens, updated = _BUCKETS.get(provider, (float(rate), now))
            tokens = min(float(rate), tokens + (now - updated) * rate / 60)
            if tokens >= 1:
                _BUCKETS[provider] = (tokens - 1, now)
                return
            wait = (1 - tokens) * 60 / rate
            _BUCKETS[provider] = (tokens, now)
        time.sleep(wait)


def _transition(repos, task_id: int, state: TaskState, error: str = "") -> None:
    repos.tasks.transition(task_id, state, error=error)


def _retry_or_dead_letter(repos, task_id: int, attempt: int, error: str) -> TaskState:
    state, _ = on_failure(TaskState.RUNNING, max(0, attempt - 1))
    _transition(repos, task_id, state, error)
    return state


def _resource(repos, task_row: dict) -> dict:
    embedded = task_row.get("resource")
    if embedded is not None:
        return embedded
    getter = getattr(repos, "get_resource", None)
    if getter is None:
        raise LookupError("repos.get_resource is required for resource_id")
    result = getter(task_row["resource_id"])
    if result is None:
        raise LookupError(f"discovered_resource {task_row.get('resource_id')} not found")
    return result


def execute_transfer(session, task_row, *, drives, repos, settings) -> dict:
    """Run one share transfer and persist each recognized media episode.

    ``task_row`` carries resource_id and media_id; repositories provide
    ``get_resource``/``get_media`` and ``library.upsert_episode_file``.
    """
    resource = _resource(repos, task_row)
    provider = str(resource["provider"]).lower()
    share_url = str(resource["share_url"])
    media_id = int(task_row.get("media_id") or resource.get("media_id") or 0)
    season = int(task_row.get("season", resource.get("season", 1)) or 1)
    episode = int(task_row.get("episode", resource.get("episode", 1)) or 1)
    bucket = str(task_row.get("quality_bucket", resource.get("quality_bucket", "sd")))
    key = str(
        task_row.get("idempotency_key")
        or idempotency_key(provider, share_url, season, episode, bucket)
    )
    task_id, _created = repos.tasks.create_or_get(
        key,
        subscription_id=task_row.get("subscription_id"),
        resource_id=task_row.get("resource_id"),
    )
    drive = drives[provider]
    with _serialize(key):
        stored = repos.tasks.get(task_id) if hasattr(repos.tasks, "get") else None
        state = str((stored or task_row).get("state", "queued"))
        if state == TaskState.SUCCEEDED.value:
            return {"ok": True, "task_id": task_id, "idempotent": True, "organized": True}
        if state == TaskState.RUNNING.value:
            return {
                "ok": False,
                "task_id": task_id,
                "state": state,
                "error": "task already running",
            }
        _transition(repos, task_id, TaskState.RUNNING)
        task_state = repos.tasks.get(task_id) if hasattr(repos.tasks, "get") else {}
        current_attempt = int((task_state or {}).get("attempt", task_row.get("attempt", 1)))
        _take_token(provider)
        try:
            status = drive.check_share(share_url, str(resource.get("password", "")))
        except Exception as error:
            state = _retry_or_dead_letter(repos, task_id, current_attempt, str(error))
            return {"ok": False, "task_id": task_id, "state": state.value, "error": str(error)}
        if not status.valid:
            error = status.error or "分享失效"
            dst = TaskState.RETRY_WAIT if status.password_required else TaskState.DEAD_LETTER
            if dst is TaskState.DEAD_LETTER:
                _transition(repos, task_id, TaskState.FAILED, error)
            _transition(repos, task_id, dst, error)
            return {"ok": False, "task_id": task_id, "state": dst.value, "error": error}

        try:
            share_files = drive.list_share_files(share_url, str(resource.get("password", "")))
        except Exception as error:
            state = _retry_or_dead_letter(repos, task_id, current_attempt, str(error))
            return {"ok": False, "task_id": task_id, "state": state.value, "error": str(error)}
        selected = []
        for item in share_files:
            parsed_season, parsed_episode = parse_episode_from_name(item.name)
            if parsed_episode is None or (
                parsed_episode == episode and (parsed_season is None or parsed_season == season)
            ):
                selected.append(item)
        if not selected:
            error = f"分享中未找到 S{season:02d}E{episode:02d} 文件"
            next_state = _retry_or_dead_letter(repos, task_id, current_attempt, error)
            return {"ok": False, "task_id": task_id, "state": next_state.value, "error": error}

        inbox_root = str(getattr(settings, "transfer_root", "CSX"))
        inbox = posixpath.join(inbox_root, "_inbox", key)
        try:
            outcome = drive.transfer(
                share_url,
                inbox,
                file_ids=[item.file_id for item in selected],
                password=str(resource.get("password", "")),
            )
        except Exception as error:
            state = _retry_or_dead_letter(repos, task_id, current_attempt, str(error))
            return {"ok": False, "task_id": task_id, "state": state.value, "error": str(error)}
        if not outcome.created:
            error = outcome.error or "转存未生成文件"
            next_state = _retry_or_dead_letter(repos, task_id, current_attempt, error)
            return {"ok": False, "task_id": task_id, "state": next_state.value, "error": error}

        media = task_row.get("media") or repos.get_media(media_id)
        organized = True
        errors = []
        sidecars = []
        organized_dir = None
        video_exts = {"mkv", "mp4", "avi", "mov", "wmv", "ts", "m2ts", "webm", "flv"}
        for file_id, path, size, sha1 in outcome.created:
            filename = posixpath.basename(path)
            parsed_season, parsed_episode = parse_episode_from_name(filename)
            file_season = parsed_season if parsed_season is not None else season
            file_episode = parsed_episode if parsed_episode is not None else episode
            extension = posixpath.splitext(filename)[1].lstrip(".").lower()
            if extension not in video_exts:
                sidecars.append(file_id)
                continue
            repos.library.upsert_episode_file(
                media_id=media_id,
                season=file_season,
                episode=file_episode,
                path=path,
                size=size,
                sha1=sha1,
                quality_bucket=bucket,
            )
            file_row = {
                "file_id": file_id,
                "season": file_season,
                "episode": file_episode,
                "extension": extension or "mkv",
                "quality_bucket": bucket,
                "resource_kind": resource.get("resource_kind", "episode"),
                "release_date": _release_date(resource.get("release_date")),
            }
            try:
                target_path = organize_file(
                    drive,
                    file_row,
                    media,
                    library_root=str(getattr(settings, "library_root", "")),
                )
                repos.library.update_path(file_id=file_id, old_path=path, new_path=target_path)
                organized_dir = posixpath.dirname(target_path)
            except Exception as error:  # organization retry must not undo landed files
                organized = False
                errors.append(str(error))
        if organized_dir:
            for file_id in sidecars:
                try:
                    drive.move(file_id, organized_dir)
                except Exception as error:  # sidecar errors do not undo landed media
                    organized = False
                    errors.append(str(error))

        if not outcome.ok:
            error = outcome.error or "部分文件转存失败"
            next_state = _retry_or_dead_letter(repos, task_id, current_attempt, error)
            return {
                "ok": False,
                "task_id": task_id,
                "state": next_state.value,
                "organized": organized,
                "error": error,
            }
        _transition(repos, task_id, TaskState.SUCCEEDED)
        return {
            "ok": True,
            "task_id": task_id,
            "organized": organized,
            "organize_errors": errors,
            "created": outcome.created,
        }


def _release_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
