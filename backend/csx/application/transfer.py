"""Idempotent transfer orchestration with explicit task state transitions."""

from __future__ import annotations

import logging
import posixpath
import threading
import time
import traceback
from contextlib import contextmanager
from datetime import date

from csx.application.naming import select_template
from csx.application.organize import organize_file, resolve_category
from csx.domain.naming import parse_episode_from_name
from csx.domain.resource import idempotency_key
from csx.domain.task import TaskState, on_failure
from csx.domain.upgrade import UpgradeAction, decide_upgrade
from csx.ports.drive import TransferOutcome

logger = logging.getLogger(__name__)

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


_VIDEO_SUFFIXES = (
    ".mkv",
    ".mp4",
    ".ts",
    ".m2ts",
    ".avi",
    ".rmvb",
    ".mov",
    ".wmv",
    ".iso",
)


def _fmt_error(error: BaseException) -> str:
    """把异常连同最内层堆栈位置写进任务错误，便于线上定位。"""
    tail = traceback.format_exc().strip().splitlines()
    where = next(
        (line.strip() for line in reversed(tail) if line.strip().startswith(("File ", "  "))), ""
    )
    message = f"{type(error).__name__}: {error}"
    return f"{message} @ {where}" if where else message


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


def _default_inbox_root(settings) -> str:
    """账号未配置转存路径时的回退：`<CSX_TRANSFER_ROOT>/_inbox`。"""
    root = str(getattr(settings, "transfer_root", "CSX") or "").strip().strip("/")
    return "/" + posixpath.join(root, "_inbox") if root else "/_inbox"


def _transfer_layout(settings, cloud_paths: dict | None) -> dict:
    """本次任务使用的转存/归档路径与分层配置，账号级配置优先。"""
    paths = cloud_paths or {}
    raw_library = str(
        paths.get("media_path") or getattr(settings, "library_root", "") or ""
    ).strip()
    library_root = "/" + raw_library.strip("/") if raw_library.strip("/") else ""
    return {
        "inbox_root": str(paths.get("transfer_path") or _default_inbox_root(settings)),
        "library_root": library_root,
        "type_folder": bool(paths.get("type_folder", False)),
        "type_movie": str(paths.get("type_movie") or "电影").strip("/") or "电影",
        "type_tv": str(paths.get("type_tv") or "电视剧").strip("/") or "电视剧",
    }


def execute_transfer(
    session,
    task_row,
    *,
    drives,
    repos,
    settings,
    cloud_paths=None,
    naming=None,
    categories=None,
    target_provider: str = "",
    target_drive=None,
    target_cloud_paths=None,
    cross_service=None,
) -> dict:
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
    library_lookup = getattr(repos.library, "get_episode_file", None)
    existing_file = (
        library_lookup(media_id=media_id, season=season, episode=episode)
        if library_lookup is not None and media_id
        else None
    )
    upgrade_decision = None
    if existing_file:
        upgrade_decision = decide_upgrade(
            existing_file.get("quality_bucket"),
            bucket,
            upgrade_enabled=bool(resource.get("upgrade_enabled", True)),
        )
    drive = drives[provider]
    target_provider = str(target_provider or "").lower()
    cross_ready = bool(
        cross_service
        and target_provider
        and target_provider != provider
        and target_drive is not None
        and target_provider in drives
    )
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
        if resource.get("manual_transfer"):
            current = repos.tasks.get(task_id) if hasattr(repos.tasks, "get") else {}
            current_attempt = int((current or {}).get("attempt", task_row.get("attempt", 1)))
            _take_token(provider)
            try:
                status = drive.check_share(share_url, str(resource.get("password", "")))
                if not status.valid:
                    error = status.error or "分享失效"
                    next_state = _retry_or_dead_letter(repos, task_id, current_attempt, error)
                    return {
                        "ok": False,
                        "task_id": task_id,
                        "state": next_state.value,
                        "error": error,
                    }
                outcome = drive.transfer(
                    share_url,
                    str(resource["target_dir"]),
                    file_ids=[str(file_id) for file_id in resource["file_ids"]],
                    password=str(resource.get("password", "")),
                )
            except Exception as error:
                next_state = _retry_or_dead_letter(repos, task_id, current_attempt, str(error))
                return {
                    "ok": False,
                    "task_id": task_id,
                    "state": next_state.value,
                    "error": str(error),
                }
            if not outcome.ok:
                error = outcome.error or "部分文件转存失败"
                next_state = _retry_or_dead_letter(repos, task_id, current_attempt, error)
                return {"ok": False, "task_id": task_id, "state": next_state.value, "error": error}
            _transition(repos, task_id, TaskState.SUCCEEDED)
            return {
                "ok": True,
                "task_id": task_id,
                "manual": True,
                "target_dir": str(resource["target_dir"]),
                "created": outcome.created,
            }
        if upgrade_decision and upgrade_decision.action is not UpgradeAction.UPGRADE:
            _transition(repos, task_id, TaskState.CANCELLED, upgrade_decision.action.value)
            ignore = getattr(repos, "ignore_resource", None)
            if ignore is not None:
                ignore(int(task_row["resource_id"]), "ignored_low_quality")
            return {
                "ok": False,
                "task_id": task_id,
                "state": upgrade_decision.action.value,
                "candidate_state": "ignored_low_quality",
                "existing_bucket": upgrade_decision.existing_bucket,
                "candidate_bucket": upgrade_decision.candidate_bucket,
            }
        task_state = repos.tasks.get(task_id) if hasattr(repos.tasks, "get") else {}
        current_attempt = int((task_state or {}).get("attempt", task_row.get("attempt", 1)))
        _take_token(provider)
        try:
            status = drive.check_share(share_url, str(resource.get("password", "")))
        except Exception as error:
            detail = _fmt_error(error)
            state = _retry_or_dead_letter(repos, task_id, current_attempt, detail)
            return {"ok": False, "task_id": task_id, "state": state.value, "error": detail}
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
            detail = _fmt_error(error)
            state = _retry_or_dead_letter(repos, task_id, current_attempt, detail)
            return {"ok": False, "task_id": task_id, "state": state.value, "error": detail}
        media_row = (
            task_row.get("media")
            or (repos.get_media(media_id) if media_id and hasattr(repos, "get_media") else None)
            or {}
        )
        media_type = str((media_row or {}).get("type") or "").lower()
        selected = []
        unparsed = []
        if media_type == "movie":
            # 电影没有季集，取分享内全部视频文件，忽略图片与字幕
            selected = [
                item
                for item in share_files
                if not item.is_dir and item.name.lower().endswith(_VIDEO_SUFFIXES)
            ]
            if not selected:
                selected = share_files[:1]
        else:
            for item in share_files:
                parsed_season, parsed_episode = parse_episode_from_name(item.name)
                if parsed_episode is None:
                    unparsed.append(item)
                    continue
                if parsed_episode == episode and (parsed_season is None or parsed_season == season):
                    selected.append(item)
            # 解析不出集数时只在“整包分享”（仅一个文件）情况下兜底，避免误转存整季
            if not selected and len(share_files) == 1:
                selected = unparsed[:1]
        if not selected:
            if not share_files:
                error = "分享文件列表为空（115 可能限流或分享不可读）"
            else:
                error = f"分享中未找到 S{season:02d}E{episode:02d} 文件"
            next_state = _retry_or_dead_letter(repos, task_id, current_attempt, error)
            return {"ok": False, "task_id": task_id, "state": next_state.value, "error": error}

        layout = _transfer_layout(settings, cloud_paths)
        target_layout = _transfer_layout(settings, target_cloud_paths) if cross_ready else layout
        category = resolve_category(media_row or {}, categories)
        inbox = posixpath.join(layout["inbox_root"], key)
        target_inbox = posixpath.join(target_layout["inbox_root"], key)
        try:
            outcome = drive.transfer(
                share_url,
                inbox,
                file_ids=[item.file_id for item in selected],
                password=str(resource.get("password", "")),
            )
        except Exception as error:
            detail = _fmt_error(error)
            state = _retry_or_dead_letter(repos, task_id, current_attempt, detail)
            return {"ok": False, "task_id": task_id, "state": state.value, "error": detail}
        if not outcome.created:
            error = outcome.error or "转存未生成文件"
            next_state = _retry_or_dead_letter(repos, task_id, current_attempt, error)
            return {"ok": False, "task_id": task_id, "state": next_state.value, "error": error}

        if cross_ready:
            relayed: list[tuple[str, str, int, str]] = []
            relay_error = ""
            for _file_id, path, _size, _sha1 in outcome.created:
                name = posixpath.basename(path)
                try:
                    item = cross_service.relay(
                        provider,
                        inbox,
                        name,
                        target_provider,
                        target_inbox,
                        name,
                        parent_task_id=str(task_id),
                    )
                except Exception as error:  # 中继失败整单重试，不落半截
                    relay_error = _fmt_error(error)
                    break
                relayed.append((item["file_id"], item["path"], item["size"], item["sha1"]))
                try:
                    drive.delete_path(path)
                except Exception as error:  # 源盘中转清理失败只记日志
                    logger.warning(f"清理源盘中转文件失败 {path}：{error}")
            if relay_error:
                state = _retry_or_dead_letter(repos, task_id, current_attempt, relay_error)
                return {
                    "ok": False,
                    "task_id": task_id,
                    "state": state.value,
                    "error": relay_error,
                }
            outcome = TransferOutcome(ok=True, created=relayed)
            drive = target_drive
            layout = target_layout

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
                provider=target_provider if cross_ready else provider,
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
            episode_title = ""
            title_lookup = getattr(repos, "get_episode_title", None)
            if title_lookup is not None:
                try:
                    episode_title = str(title_lookup(media_id, file_season, file_episode) or "")
                except Exception:  # 单集标题只是模板变量，查不到不影响整理
                    episode_title = ""
            try:
                target_path = organize_file(
                    drive,
                    file_row,
                    media,
                    category=category,
                    library_root=layout["library_root"],
                    type_folder=layout["type_folder"],
                    type_movie=layout["type_movie"],
                    type_tv=layout["type_tv"],
                    template=select_template(
                        naming, media.get("type"), file_row.get("resource_kind")
                    ),
                    episode_title=episode_title,
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
            "is_upgrade": bool(existing_file and upgrade_decision and upgrade_decision.is_upgrade),
            "existing_bucket": existing_file.get("quality_bucket", "") if existing_file else "",
            "quality_bucket": bucket,
            "season": season,
            "episode": episode,
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
