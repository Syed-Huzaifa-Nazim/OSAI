"""Cancellable background jobs: scraping (stages 2-3) and Find gaps (stage 4).

How it works:
  * ``begin`` registers a job and keeps the project's state from BEFORE the run, so a cancel can put it back.
  * Long steps call ``checkpoint()`` (Daraz requests, Daraz search, reviews, the Apify run...). After a cancel it
    raises ``JobCancelled``, which stops the job within a few seconds.
  * The job never writes its results while it runs (``staging.StagedRepository`` holds them); everything is written
    at the end, inside ``guard()``. A cancel takes the same lock, so a cancel and the final write never overlap:
    either the whole result is saved, or nothing of it is.

One server process runs the jobs (FastAPI background tasks), so an in-memory registry is enough.
"""
from __future__ import annotations

import contextvars
import threading
from contextlib import contextmanager
from typing import Any, Iterator


class JobCancelled(BaseException):
    """Raised inside a cancelled job. A BaseException, so per-layer ``except Exception`` blocks never swallow it."""


_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_current: contextvars.ContextVar[str | None] = contextvars.ContextVar("optistratix_job", default=None)


def begin(project_id: str, previous: dict[str, Any]) -> None:
    """Registers a job. ``previous`` = {"state": pipeline state, "project": {status, current_stage, gap_count}}."""
    with _lock:
        _jobs[project_id] = {"cancelled": threading.Event(), "guard": threading.Lock(), "previous": previous}


def bind(project_id: str) -> None:
    """Marks the running code (and every thread it starts) as belonging to this project's job."""
    _current.set(project_id)


def carry(fn: Any) -> Any:
    """Wraps work handed to a plain thread pool so it still belongs to this job (pools do not copy context)."""
    project_id = _current.get()

    def run(*args: Any, **kwargs: Any) -> Any:
        if project_id:
            _current.set(project_id)
            checkpoint(project_id)
        return fn(*args, **kwargs)

    return run


def finish(project_id: str) -> None:
    with _lock:
        _jobs.pop(project_id, None)


def running(project_id: str) -> bool:
    with _lock:
        job = _jobs.get(project_id)
    return bool(job) and not job["cancelled"].is_set()


def is_cancelled(project_id: str | None = None) -> bool:
    project_id = project_id or _current.get()
    if not project_id:
        return False
    with _lock:
        job = _jobs.get(project_id)
    return bool(job) and job["cancelled"].is_set()


def checkpoint(project_id: str | None = None) -> None:
    """Stops the current job if it was cancelled. Does nothing outside a job."""
    if is_cancelled(project_id):
        raise JobCancelled(project_id or _current.get())


def cancel(project_id: str) -> dict[str, Any] | None:
    """Cancels a running job and returns the state from before it started (None when no job is running).

    Waits for a final write that is already under way, so the result is all or nothing.
    """
    with _lock:
        job = _jobs.get(project_id)
    if not job:
        return None
    with job["guard"]:
        # A successful worker can finish while cancel waits for the guard.
        # In that case the completed result must not be rolled back.
        with _lock:
            if _jobs.get(project_id) is not job:
                return None
        job["cancelled"].set()
    return job["previous"]


@contextmanager
def guard(project_id: str) -> Iterator[None]:
    """Wraps every database write a job makes: refused after a cancel, never interleaved with one."""
    with _lock:
        job = _jobs.get(project_id)
    if not job:
        yield
        return
    with job["guard"]:
        if job["cancelled"].is_set():
            raise JobCancelled(project_id)
        yield
