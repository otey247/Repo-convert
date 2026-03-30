"""Git operations: clone, init, and publish repositories.

Tokens are never written to log output.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlparse, urlunparse

import requests
from git import GitCommandError, InvalidGitRepositoryError, Repo

logger = logging.getLogger(__name__)

# Regex used to redact tokens from log messages
_TOKEN_RE = re.compile(r"(https?://)([^@]+)@")


def _redact(url: str) -> str:
    """Replace embedded credentials in a URL with ``***``."""
    return _TOKEN_RE.sub(r"\1***@", url)


def _inject_token(url: str, token: str) -> str:
    """Return a URL with *token* embedded as the userinfo component.

    Args:
        url: HTTPS repository URL (must start with ``https://``).
        token: GitHub personal access token.

    Returns:
        URL suitable for authenticated git operations.

    Raises:
        ValueError: If the URL scheme is not HTTPS.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS URLs are supported for token injection.")
    port_suffix = f":{parsed.port}" if parsed.port else ""
    authed = parsed._replace(netloc=f"{token}@{parsed.hostname}{port_suffix}")
    return urlunparse(authed)


def clone_repo(url: str, dest_dir: str, token: Optional[str] = None) -> str:
    """Clone a remote git repository to *dest_dir*.

    For private repositories supply a *token*; it is embedded in the URL
    and is **never** written to any log.

    Args:
        url: Remote repository URL (HTTPS).
        dest_dir: Local directory where the repo will be cloned.
        token: Optional PAT for private repositories.

    Returns:
        Absolute path to the cloned repository root.

    Raises:
        GitCommandError: If the clone operation fails.
    """
    clone_url = _inject_token(url, token) if token else url
    logger.info("Cloning %s into %s", _redact(clone_url), dest_dir)
    try:
        repo = Repo.clone_from(clone_url, dest_dir)
    except GitCommandError as exc:
        # Re-raise without exposing the token
        safe_msg = str(exc).replace(token, "***") if token else str(exc)
        raise GitCommandError(safe_msg, exc.status) from None
    return str(repo.working_dir)


def init_repo(directory: str) -> None:
    """Initialise a new git repository in *directory*.

    Args:
        directory: Path to the directory that should become a git repo.

    Raises:
        InvalidGitRepositoryError: If git init fails unexpectedly.
    """
    logger.info("Initialising git repository in %s", directory)
    Repo.init(directory)


def publish_repo(
    local_dir: str,
    repo_name: str,
    token: str,
    description: str = "",
) -> str:
    """Create a new GitHub repository and push *local_dir* to it.

    Workflow:
    1. Create the remote repo via the GitHub REST API.
    2. ``git init`` the local directory (if not already a repo).
    3. Stage all files, create an initial commit, and push to ``main``.

    Args:
        local_dir: Path to the converted repository on disk.
        repo_name: Desired name for the new GitHub repository.
        token: GitHub PAT with ``repo`` scope — **never logged**.
        description: Optional repository description.

    Returns:
        HTTPS URL of the newly created GitHub repository.

    Raises:
        requests.HTTPError: If the GitHub API returns an error.
        GitCommandError: If push fails.
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    payload = {"name": repo_name, "description": description, "private": False}

    logger.info("Creating GitHub repository '%s'", repo_name)
    response = requests.post(
        "https://api.github.com/user/repos",
        json=payload,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    repo_data = response.json()
    remote_url = repo_data["clone_url"]
    authed_url = _inject_token(remote_url, token)

    logger.info("Pushing to %s", _redact(authed_url))
    try:
        repo = Repo(local_dir)
    except InvalidGitRepositoryError:
        repo = Repo.init(local_dir)

    repo.git.add(A=True)
    if repo.is_dirty(index=True, untracked_files=True):
        repo.index.commit("Initial commit — converted by Repo-convert")

    origin_name = "origin"
    if origin_name in [r.name for r in repo.remotes]:
        repo.delete_remote(origin_name)
    origin = repo.create_remote(origin_name, authed_url)

    try:
        origin.push(refspec="HEAD:refs/heads/main")
    except GitCommandError as exc:
        safe_msg = str(exc).replace(token, "***")
        raise GitCommandError(safe_msg, exc.status) from None

    return repo_data["html_url"]
