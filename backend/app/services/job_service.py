"""Background job management.

Jobs are executed in daemon threads.  State is kept in an in-memory
dictionary keyed by UUID job IDs.  Temporary working directories are
cleaned up either after the converted ZIP has been downloaded, or
automatically after ``MAX_JOB_AGE_HOURS`` hours via a periodic reaper
thread started at import time.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from app.models.schemas import (
    ConversionSummary,
    JobState,
    JobStatus,
    SourceType,
)
from app.services.converter import convert_repository
from app.services.git_service import clone_repo
from app.services.zip_service import create_zip, extract_zip

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_jobs: Dict[str, JobState] = {}
_jobs_lock = threading.Lock()

# How many seconds until an uncollected job's temp dir is removed
_MAX_JOB_AGE_SECS: float = float(os.getenv("MAX_JOB_AGE_HOURS", "1")) * 3600


# ---------------------------------------------------------------------------
# Reaper
# ---------------------------------------------------------------------------


def _reaper() -> None:
    """Periodically remove stale job working directories."""
    while True:
        time.sleep(300)  # check every 5 minutes
        _evict_stale_jobs()


def _evict_stale_jobs() -> None:
    """Remove temp dirs for jobs older than ``_MAX_JOB_AGE_SECS``.

    Only terminal jobs (completed/failed) are eligible for eviction so that
    long-running or stuck processing jobs are not cleaned up mid-run.
    """
    now = time.time()
    with _jobs_lock:
        stale = [
            jid
            for jid, state in _jobs.items()
            if (
                state.created_at
                and (now - state.created_at) > _MAX_JOB_AGE_SECS
                and state.status in (JobStatus.completed, JobStatus.failed)
            )
        ]
    for jid in stale:
        _cleanup_job(jid)
        logger.info("Evicted stale job %s", jid)


_reaper_thread = threading.Thread(target=_reaper, daemon=True, name="job-reaper")
_reaper_thread.start()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def submit_job(
    source_type: SourceType,
    github_url: Optional[str] = None,
    github_token: Optional[str] = None,
    source_zip_path: Optional[str] = None,
) -> str:
    """Create a new job and start it in a background thread.

    Args:
        source_type: Where the repository comes from.
        github_url: Remote URL (required for GitHub source types).
        github_token: PAT for private repositories — never logged.
        source_zip_path: Local path to an uploaded ZIP (zip_upload only).

    Returns:
        A UUID string identifying the new job.
    """
    job_id = str(uuid.uuid4())
    state = JobState(
        job_id=job_id,
        status=JobStatus.pending,
        source_type=source_type,
        github_url=github_url,
        github_token=github_token,
        source_zip_path=source_zip_path,
        created_at=time.time(),
    )
    with _jobs_lock:
        _jobs[job_id] = state

    thread = threading.Thread(target=_run_job, args=(job_id,), daemon=True, name=f"job-{job_id}")
    thread.start()
    logger.info("Submitted job %s (source_type=%s)", job_id, source_type)
    return job_id


def get_job(job_id: str) -> Optional[JobState]:
    """Return the :class:`JobState` for *job_id*, or ``None`` if not found.

    Args:
        job_id: UUID of the job.

    Returns:
        The current job state or ``None``.
    """
    with _jobs_lock:
        return _jobs.get(job_id)


def mark_downloaded(job_id: str) -> None:
    """Signal that the caller has downloaded the ZIP; schedule cleanup.

    The cleanup is deferred by 60 seconds to avoid racing with the
    in-progress file stream.

    Args:
        job_id: UUID of the job whose output has been collected.
    """
    def _deferred():
        time.sleep(60)
        _cleanup_job(job_id)

    threading.Thread(target=_deferred, daemon=True, name=f"cleanup-{job_id}").start()


def cleanup_all() -> None:
    """Remove all job working directories.  Called on application shutdown."""
    with _jobs_lock:
        job_ids = list(_jobs.keys())
    for jid in job_ids:
        _cleanup_job(jid)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _update(job_id: str, **kwargs) -> None:
    """Atomically update fields on the stored :class:`JobState`."""
    with _jobs_lock:
        state = _jobs.get(job_id)
        if state is None:
            return
        for key, value in kwargs.items():
            setattr(state, key, value)


def _cleanup_job(job_id: str) -> None:
    """Remove the working directory for *job_id* and delete its state."""
    with _jobs_lock:
        state = _jobs.pop(job_id, None)
    if state and state.work_dir and Path(state.work_dir).exists():
        shutil.rmtree(state.work_dir, ignore_errors=True)
        logger.debug("Cleaned up work_dir for job %s", job_id)
    if state and state.source_zip_path and os.path.exists(state.source_zip_path):
        try:
            os.remove(state.source_zip_path)
            logger.debug("Cleaned up source_zip_path for job %s", job_id)
        except OSError as exc:
            logger.warning(
                "Failed to remove source_zip_path %s for job %s: %s",
                state.source_zip_path,
                job_id,
                exc,
            )


def _run_job(job_id: str) -> None:
    """Execute the full conversion pipeline for *job_id*.

    This runs in a background thread.  Progress is written back to the
    in-memory store at key checkpoints so that polling clients see
    fine-grained updates.

    Args:
        job_id: UUID of the job to process.
    """
    state = get_job(job_id)
    if state is None:
        return

    _update(job_id, status=JobStatus.processing, progress=5)

    work_dir = tempfile.mkdtemp(prefix=f"repo-convert-{job_id[:8]}-")
    _update(job_id, work_dir=work_dir)

    source_dir = os.path.join(work_dir, "source")
    output_dir = os.path.join(work_dir, "output")
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # ------------------------------------------------------------------
        # Step 1 – acquire source
        # ------------------------------------------------------------------
        if state.source_type in (SourceType.github_public, SourceType.github_private):
            if not state.github_url:
                raise ValueError("github_url is required for GitHub source types.")
            _update(job_id, progress=15)
            clone_repo(
                url=state.github_url,
                dest_dir=source_dir,
                token=state.github_token,
            )
        elif state.source_type == SourceType.zip_upload:
            if not state.source_zip_path:
                raise ValueError("source_zip_path is required for zip_upload.")
            _update(job_id, progress=15)
            extract_zip(state.source_zip_path, source_dir)
        else:
            raise ValueError(f"Unsupported source_type: {state.source_type}")

        _update(job_id, progress=40)

        # ------------------------------------------------------------------
        # Step 2 – detect repo name
        # ------------------------------------------------------------------
        repo_name = _detect_repo_name(state)

        # ------------------------------------------------------------------
        # Step 3 – convert
        # ------------------------------------------------------------------
        _update(job_id, progress=50)
        conversion = convert_repository(source_dir, output_dir)
        _update(job_id, progress=80)

        # ------------------------------------------------------------------
        # Step 4 – build preview mappings
        # ------------------------------------------------------------------
        preview_mappings = [
            {"source_path": src, "output_path": dst, "action": action}
            for src, dst, action in conversion.mappings
        ]

        # ------------------------------------------------------------------
        # Step 5 – zip output
        # ------------------------------------------------------------------
        output_zip = os.path.join(work_dir, f"{repo_name}-converted.zip")
        create_zip(output_dir, output_zip)
        _update(job_id, progress=95)

        # ------------------------------------------------------------------
        # Finalise
        # ------------------------------------------------------------------
        summary = ConversionSummary(
            total_files=conversion.total_files,
            md_files_converted=conversion.md_converted,
            output_repo_name=f"{repo_name}-converted",
            skipped_files=conversion.skipped,
            errors=conversion.errors,
        )
        _update(
            job_id,
            status=JobStatus.completed,
            progress=100,
            summary=summary,
            output_zip_path=output_zip,
            preview_mappings=preview_mappings,
        )
        logger.info(
            "Job %s completed: %d files, %d converted",
            job_id,
            conversion.total_files,
            conversion.md_converted,
        )

    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed with %s", job_id, type(exc).__name__)
        _update(
            job_id,
            status=JobStatus.failed,
            error_message=str(exc),
            summary=ConversionSummary(errors=[str(exc)]),
        )


def _detect_repo_name(state: JobState) -> str:
    """Derive a friendly repository name from the job source.

    Args:
        state: Current job state.

    Returns:
        A sanitised repository name string.
    """
    if state.github_url:
        name = state.github_url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name or "repository"
    if state.source_zip_path:
        base = Path(state.source_zip_path).stem
        return base or "repository"
    return "repository"
