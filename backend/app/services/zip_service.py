"""ZIP import and export utilities.

Extraction is hardened against path-traversal attacks: any member whose
resolved path falls outside the destination directory is skipped.
"""

from __future__ import annotations

import logging
import os
import posixpath
import shutil
import zipfile
from pathlib import Path, PurePosixPath

logger = logging.getLogger(__name__)


def extract_zip(zip_path: str, dest_dir: str) -> str:
    """Safely extract a ZIP archive to *dest_dir*.

    Each member is checked to ensure its final path resolves inside
    *dest_dir*.  Members that would escape the destination (path-traversal
    attack) are silently skipped and a warning is logged.

    Args:
        zip_path: Path to the source ``.zip`` file.
        dest_dir: Directory where the archive will be extracted.

    Returns:
        Absolute path to *dest_dir* (created if necessary).

    Raises:
        zipfile.BadZipFile: If *zip_path* is not a valid ZIP archive.
        FileNotFoundError: If *zip_path* does not exist.
    """
    dest = Path(dest_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            # Normalise separators: treat name as POSIX, replace backslashes,
            # reject drive letters / UNC paths to harden against traversal.
            raw_name = member.filename.replace("\\", "/")
            # Reject Windows drive letters (e.g. "C:/...") and UNC paths
            if len(raw_name) >= 2 and raw_name[1] == ":":
                logger.warning("Skipping member with drive letter: %s", member.filename)
                continue
            if raw_name.startswith("//"):
                logger.warning("Skipping UNC-style member: %s", member.filename)
                continue
            # Normalise (collapse .., redundant slashes) via posixpath
            normalised = posixpath.normpath(raw_name)
            if normalised.startswith("..") or normalised.startswith("/"):
                logger.warning(
                    "Skipping potentially unsafe ZIP member: %s", member.filename
                )
                continue

            member_path = dest / PurePosixPath(normalised)
            resolved = member_path.resolve()

            try:
                resolved.relative_to(dest)
            except ValueError:
                logger.warning(
                    "Skipping potentially unsafe ZIP member: %s", member.filename
                )
                continue

            if member.is_dir():
                resolved.mkdir(parents=True, exist_ok=True)
            else:
                resolved.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, resolved.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

    logger.info("Extracted %s to %s", zip_path, dest)
    return str(dest)


def create_zip(source_dir: str, output_zip_path: str) -> str:
    """Create a ZIP archive containing all files under *source_dir*.

    Args:
        source_dir: Root directory whose contents will be archived.
        output_zip_path: Desired path for the resulting ``.zip`` file.

    Returns:
        Absolute path to the created ZIP file.

    Raises:
        FileNotFoundError: If *source_dir* does not exist.
    """
    src = Path(source_dir).resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"source_dir not found: {src}")

    out = Path(output_zip_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src):
            for filename in files:
                abs_path = Path(root) / filename
                arcname = abs_path.relative_to(src)
                zf.write(abs_path, arcname)

    logger.info("Created ZIP %s from %s", out, src)
    return str(out)
