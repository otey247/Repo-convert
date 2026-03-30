"""Markdown-to-plain-text conversion logic.

Converts all .md / .MD files in a source directory to .txt files in an
output directory while preserving the full directory structure.  All
other non-binary files are copied unchanged.  The source directory is
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


def _resolve_output_path(output_dir: Path, rel_path: Path) -> Path:
    """Compute the output path for an .md source file.

    If an identically-named .txt already exists at the destination we use
    ``<stem>.converted.txt`` to avoid clobbering it.

    Args:
        output_dir: Root of the output directory tree.
        rel_path: Relative path of the source .md file.

    Returns:
        Absolute output path with a .txt extension.
    """
    candidate = output_dir / rel_path.with_suffix(".txt")
    if candidate.exists():
        candidate = output_dir / rel_path.with_name(rel_path.stem + ".converted.txt")
    return candidate


def _collect_files(source_dir: Path) -> List[Path]:
    """Walk *source_dir* and return all regular files (relative paths)."""
    files: List[Path] = []
    for root, _, filenames in os.walk(source_dir):
        for name in filenames:
            abs_path = Path(root) / name
            files.append(abs_path.relative_to(source_dir))
    return sorted(files)


def convert_repository(source_dir: str, output_dir: str) -> ConversionResult:
    """Convert a repository by turning .md files into .txt files.

    Recursively scans *source_dir*.  For every ``.md`` / ``.MD`` file the
    content is copied to *output_dir* with a ``.txt`` extension.  All other
    non-binary files are copied as-is.  Binary files without a Markdown
    extension are skipped.  The original *source_dir* is never modified.

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

    result = ConversionResult()

    for rel_path in _collect_files(src):
        abs_src = src / rel_path
        result.total_files += 1

        try:
            is_md = rel_path.suffix.lower() == ".md"

            if is_md:
                abs_dst = _resolve_output_path(out, rel_path)
                abs_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(abs_src, abs_dst)
                rel_dst = abs_dst.relative_to(out)
                result.md_converted += 1
                result.mappings.append((str(rel_path), str(rel_dst), "convert"))
                logger.debug("Converted %s -> %s", rel_path, rel_dst)

            elif _is_binary(abs_src):
                result.skipped.append(str(rel_path))
                result.mappings.append((str(rel_path), "", "skip"))
                logger.debug("Skipped binary file: %s", rel_path)

            else:
                abs_dst = out / rel_path
                abs_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(abs_src, abs_dst)
                result.mappings.append((str(rel_path), str(rel_path), "copy"))
                logger.debug("Copied %s", rel_path)

        except (OSError, IOError, PermissionError, shutil.Error) as exc:
            msg = f"{rel_path}: {exc}"
            result.errors.append(msg)
            logger.warning("Error processing file: %s", msg)

    return result
