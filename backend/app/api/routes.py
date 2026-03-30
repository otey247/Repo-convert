"""All API routes for the Repo-convert application.

Endpoints
---------
POST   /api/jobs                     – Submit a conversion job
GET    /api/jobs/{job_id}            – Poll job status
GET    /api/jobs/{job_id}/download   – Download converted ZIP
POST   /api/jobs/{job_id}/publish    – Publish result to GitHub
GET    /api/jobs/{job_id}/preview    – Preview file mappings
"""

from __future__ import annotations

import logging
import os
import tempfile
import shutil
from typing import Optional

import requests
from git import GitCommandError
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.models.schemas import (
    FileMapping,
    JobStatus,
    JobStatusResponse,
    JobSubmitResponse,
    PreviewResponse,
    PublishRequest,
    PublishResponse,
    SourceType,
)
from app.services import git_service, job_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_job(job_id: str):
    """Return the job state or raise 404.

    Args:
        job_id: UUID of the requested job.

    Returns:
        The :class:`~app.models.schemas.JobState` instance.

    Raises:
        HTTPException: 404 when *job_id* is not found.
    """
    state = job_service.get_job(job_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return state


# ---------------------------------------------------------------------------
# POST /api/jobs
# ---------------------------------------------------------------------------


@router.post("/jobs", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    source_type: SourceType = Form(...),
    github_url: Optional[str] = Form(None),
    github_token: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Submit a new conversion job.

    Accepts ``multipart/form-data`` with the following fields:

    - **source_type** *(required)*: ``github_public`` | ``github_private`` | ``zip_upload``
    - **github_url**: Repository URL (required for GitHub source types)
    - **github_token**: PAT for private repos — **never logged**
    - **file**: Uploaded ZIP archive (required for ``zip_upload``)

    Returns the new job ID and its initial ``pending`` status.
    """
    source_zip_path: Optional[str] = None

    if source_type == SourceType.zip_upload:
        if file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A ZIP file must be uploaded when source_type is 'zip_upload'.",
            )
        # Persist the upload to a temp file so the background thread can read it.
        # Stream in chunks to avoid loading the entire archive into memory.
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip", prefix="upload-")
        try:
            shutil.copyfileobj(file.file, tmp, length=64 * 1024)
            tmp.flush()
            source_zip_path = tmp.name
        finally:
            tmp.close()

    elif source_type in (SourceType.github_public, SourceType.github_private):
        if not github_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="github_url is required for GitHub source types.",
            )
        if source_type == SourceType.github_private and not github_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="github_token is required for github_private source type.",
            )

    job_id = job_service.submit_job(
        source_type=source_type,
        github_url=github_url,
        github_token=github_token,
        source_zip_path=source_zip_path,
    )
    return JobSubmitResponse(job_id=job_id, status=JobStatus.pending)


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    """Return the current status and progress of a job.

    Args:
        job_id: UUID returned by ``POST /api/jobs``.

    Returns:
        Full status payload including optional conversion summary.
    """
    state = _require_job(job_id)
    return JobStatusResponse(
        job_id=state.job_id,
        status=state.status,
        progress=state.progress,
        summary=state.summary,
        error_message=state.error_message,
    )


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}/download
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/download")
def download_job(job_id: str):
    """Stream the converted repository as a ZIP file.

    The download is only available once the job has reached
    ``completed`` status.  A one-time cleanup is scheduled after the
    response is sent.

    Args:
        job_id: UUID of the completed job.

    Returns:
        ZIP file attachment.

    Raises:
        HTTPException: 400 if the job is not yet complete; 404 if not found.
    """
    state = _require_job(job_id)

    if state.status != JobStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not complete yet (status={state.status}).",
        )

    if not state.output_zip_path or not os.path.isfile(state.output_zip_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Output ZIP not found; the job may have been cleaned up.",
        )

    filename = os.path.basename(state.output_zip_path)
    job_service.mark_downloaded(job_id)
    return FileResponse(
        path=state.output_zip_path,
        media_type="application/zip",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /api/jobs/{job_id}/publish
# ---------------------------------------------------------------------------


@router.post("/jobs/{job_id}/publish", response_model=PublishResponse)
def publish_job(job_id: str, body: PublishRequest):
    """Publish the converted repository to GitHub.

    Creates a new GitHub repository under the authenticated user's
    account and pushes the converted files.

    Args:
        job_id: UUID of the completed job.
        body: Publish parameters (repo name, token, optional description).

    Returns:
        The HTTPS URL of the newly created repository.

    Raises:
        HTTPException: 400 if the job is not complete; 404 if not found.
    """
    state = _require_job(job_id)

    if state.status != JobStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not complete yet (status={state.status}).",
        )

    if not state.work_dir:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Working directory no longer available.",
        )

    output_dir = os.path.join(state.work_dir, "output")
    if not os.path.isdir(output_dir):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Converted output directory not found.",
        )

    try:
        repo_url = git_service.publish_repo(
            local_dir=output_dir,
            repo_name=body.repo_name,
            token=body.github_token,
            description=body.description or "",
        )
    except requests.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {exc.response.status_code} {exc.response.reason}",
        ) from None
    except GitCommandError as exc:
        safe = str(exc).replace(body.github_token, "***")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Git push failed: {safe}",
        ) from None
    except Exception as exc:  # noqa: BLE001
        safe = str(exc).replace(body.github_token, "***")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to publish repository: {safe}",
        ) from None

    return PublishResponse(repo_url=repo_url)


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}/preview
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/preview", response_model=PreviewResponse)
def preview_job(job_id: str):
    """Return the list of files that will be (or were) converted.

    Available once the job has started processing.

    Args:
        job_id: UUID of the job.

    Returns:
        Before/after file mapping list.

    Raises:
        HTTPException: 404 if the job is not found; 400 if not yet started.
    """
    state = _require_job(job_id)

    if state.status == JobStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview is not yet available; job is still pending.",
        )

    mappings = [
        FileMapping(
            source_path=m["source_path"],
            output_path=m["output_path"],
            action=m["action"],
        )
        for m in state.preview_mappings
    ]
    return PreviewResponse(job_id=job_id, mappings=mappings)
