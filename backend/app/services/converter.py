"""Markdown-to-plain-text conversion logic.

Converts all .md / .MD files in a source directory to .txt files in an
output directory while preserving the full directory structure. All
other non-Markdown files are copied unchanged. The source directory is
never modified.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Heuristic chunk size used to detect binary files
_BINARY_PROBE_BYTES = 8192


@dataclass
class ConversionResult:
    """Summary of a completed conversion run."""

    total_files: int = 0
    md_converted: int = 0
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    mappings: List[Tuple[str, str, str]] = field(default_factory=list)
    """Each mapping is ``(relative_source_path, relative_output_path, action)``
    where *action* is ``"convert"``, ``"copy"``, or ``"skip"``."""


def _is_binary(path: Path) -> bool:
    """Return True when *path* appears to be a binary file.

    Uses the same heuristic as ``git diff``: if the first chunk of bytes
    contains a null byte the file is treated as binary.
    """
    try:
        with path.open("rb") as fh:
            chunk = fh.read(_BINARY_PROBE_BYTES)
        return b"\x00" in chunk
    except OSError:
        return True


def _resolve_output_path(source_dir: Path, output_dir: Path, rel_path: Path) -> Path:
    """Compute the output path for an .md source file.

    Collision is detected by checking whether a sibling ``.txt`` file exists
    in the *source* tree **or** the *output* directory.  When a collision is
    found we use ``<stem>.converted.txt`` to avoid clobbering.

    Args:
        source_dir: Root of the source directory tree.
        output_dir: Root of the output directory tree.
        rel_path: Relative path of the source .md file.

    Returns:
        Absolute output path with a .txt extension.
    """
    txt_rel = rel_path.with_suffix(".txt")
    candidate = output_dir / txt_rel

    # Check if a .txt sibling exists in the source tree or was already
    # written to the output (e.g. by the first pass).
    source_collision = (source_dir / txt_rel).exists()
    output_collision = candidate.exists()

    if source_collision or output_collision:
        candidate = output_dir / rel_path.with_name(rel_path.stem + ".converted.txt")
    return candidate


_EXCLUDED_DIRS = {".git"}


def _collect_files(source_dir: Path) -> List[Path]:
    """Walk *source_dir* and return all regular files (relative paths).

    VCS metadata directories (e.g. ``.git/``) are excluded to prevent
    secret leakage (embedded PATs in ``origin`` URLs) and to keep outputs
    repository-agnostic.
    """
    files: List[Path] = []
    for root, dirs, filenames in os.walk(source_dir):
        # Prune excluded directories in-place so os.walk skips them
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
        for name in filenames:
            abs_path = Path(root) / name
            files.append(abs_path.relative_to(source_dir))
    return sorted(files)


def convert_repository(source_dir: str, output_dir: str) -> ConversionResult:
    """Convert a repository by turning .md files into .txt files.

    Uses a **two-pass** approach to avoid collisions:

    1. First pass — copy all non-Markdown files to the output tree.
    2. Second pass — convert ``.md`` / ``.MD`` files, using collision-safe
       naming when a sibling ``.txt`` already exists in the source or output.

    Non-Markdown files are copied in their original format, including
    binary assets such as documents and images. Binary ``.md`` files are
    skipped. The original *source_dir* is never modified.

    Args:
        source_dir: Absolute path to the cloned / extracted repository.
        output_dir: Absolute path where converted files will be written.

    Returns:
        A :class:`ConversionResult` with statistics and per-file mappings.
    """
    src = Path(source_dir).resolve()
    out = Path(output_dir).resolve()

    if not src.is_dir():
        raise ValueError(f"source_dir does not exist or is not a directory: {src}")

    out.mkdir(parents=True, exist_ok=True)

    all_files = _collect_files(src)
    result = ConversionResult()
    result.total_files = len(all_files)

    md_files: List[Path] = []
    non_md_files: List[Path] = []
    for rel_path in all_files:
        if rel_path.suffix.lower() == ".md":
            md_files.append(rel_path)
        else:
            non_md_files.append(rel_path)

    # ------------------------------------------------------------------
    # Pass 1 — copy non-Markdown files
    # ------------------------------------------------------------------
    for rel_path in non_md_files:
        abs_src = src / rel_path
        try:
            abs_dst = out / rel_path
            abs_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_src, abs_dst)
            result.mappings.append((str(rel_path), str(rel_path), "copy"))
            logger.debug("Copied %s", rel_path)
        except (OSError, IOError, PermissionError, shutil.Error) as exc:
            msg = f"{rel_path}: {exc}"
            result.errors.append(msg)
            logger.warning("Error processing file: %s", msg)

    # ------------------------------------------------------------------
    # Pass 2 — convert Markdown files
    # ------------------------------------------------------------------
    for rel_path in md_files:
        abs_src = src / rel_path
        try:
            if _is_binary(abs_src):
                result.skipped.append(str(rel_path))
                result.mappings.append((str(rel_path), "", "skip"))
                logger.debug("Skipped binary .md file: %s", rel_path)
                continue

            abs_dst = _resolve_output_path(src, out, rel_path)
            abs_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_src, abs_dst)
            rel_dst = abs_dst.relative_to(out)
            result.md_converted += 1
            result.mappings.append((str(rel_path), str(rel_dst), "convert"))
            logger.debug("Converted %s -> %s", rel_path, rel_dst)
        except (OSError, IOError, PermissionError, shutil.Error) as exc:
            msg = f"{rel_path}: {exc}"
            result.errors.append(msg)
            logger.warning("Error processing file: %s", msg)

    return result
