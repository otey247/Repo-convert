"""Pydantic models for request/response schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Supported repository source types."""

    github_public = "github_public"
    github_private = "github_private"
    zip_upload = "zip_upload"


class JobStatus(str, Enum):
    """Possible job lifecycle states."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# ---------------------------------------------------------------------------
# Job submission
# ---------------------------------------------------------------------------


class JobSubmitRequest(BaseModel):
    """Payload for submitting a conversion job (JSON variant)."""

    source_type: SourceType
    github_url: Optional[str] = Field(None, description="Repository URL (github types)")
    github_token: Optional[str] = Field(None, description="PAT for private repos — never logged")


class JobSubmitResponse(BaseModel):
    """Response returned immediately after job submission."""

    job_id: str
    status: JobStatus = JobStatus.pending


# ---------------------------------------------------------------------------
# Job status / summary
# ---------------------------------------------------------------------------


class ConversionSummary(BaseModel):
    """High-level statistics about a completed conversion."""

    total_files: int = 0
    md_files_converted: int = 0
    output_repo_name: str = ""
    skipped_files: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    """Full status payload returned by GET /api/jobs/{job_id}."""

    job_id: str
    status: JobStatus
    progress: int = Field(0, ge=0, le=100)
    summary: Optional[ConversionSummary] = None


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


class FileMapping(BaseModel):
    """Before/after mapping for a single file."""

    source_path: str
    output_path: str
    action: str = Field(description="'convert', 'copy', or 'skip'")


class PreviewResponse(BaseModel):
    """List of file mappings returned by GET /api/jobs/{job_id}/preview."""

    job_id: str
    mappings: List[FileMapping] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


class PublishRequest(BaseModel):
    """Payload for publishing the converted repo to GitHub."""

    repo_name: str
    github_token: str = Field(description="PAT with repo creation scope — never logged")
    description: Optional[str] = ""


class PublishResponse(BaseModel):
    """Response returned after a successful publish."""

    repo_url: str


# ---------------------------------------------------------------------------
# Internal state (not serialised directly to clients)
# ---------------------------------------------------------------------------


class JobState(BaseModel):
    """Internal state stored per job in memory."""

    job_id: str
    status: JobStatus = JobStatus.pending
    progress: int = 0
    summary: Optional[ConversionSummary] = None
    source_type: Optional[SourceType] = None
    github_url: Optional[str] = None
    # Token held in memory only — never written to logs or responses
    github_token: Optional[str] = None
    source_zip_path: Optional[str] = None
    work_dir: Optional[str] = None
    output_zip_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[float] = None
    preview_mappings: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
