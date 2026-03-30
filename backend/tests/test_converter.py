"""Tests for the Markdown-to-TXT conversion logic (converter.py)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from app.services.converter import convert_repository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(base: Path, rel: str, content: str | bytes = "content") -> Path:
    """Create a file at *base/rel* with *content*.

    Args:
        base: Base directory.
        rel: Relative path (may include sub-directories).
        content: Text or bytes to write.

    Returns:
        Absolute path to the created file.
    """
    path = base / Path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with path.open(mode) as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# 1. Basic .md → .txt conversion
# ---------------------------------------------------------------------------


def test_basic_md_to_txt_conversion():
    """A single .md file is converted to a .txt file with the same content."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), "README.md", "# Hello World\n\nSome text.")
        result = convert_repository(src, out)

        assert result.total_files == 1
        assert result.md_converted == 1
        assert len(result.errors) == 0

        txt_path = Path(out) / "README.txt"
        assert txt_path.exists(), "Expected README.txt to be created"
        assert txt_path.read_text() == "# Hello World\n\nSome text."


# ---------------------------------------------------------------------------
# 2. Nested directory structure preservation
# ---------------------------------------------------------------------------


def test_nested_directory_structure():
    """Directory hierarchy is preserved in the output."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), "docs/api/reference.md", "API docs")
        _write(Path(src), "docs/guide.md", "Guide")
        _write(Path(src), "src/module.py", "print('hello')")

        result = convert_repository(src, out)

        assert (Path(out) / "docs" / "api" / "reference.txt").exists()
        assert (Path(out) / "docs" / "guide.txt").exists()
        assert (Path(out) / "src" / "module.py").exists()
        assert result.md_converted == 2
        assert result.total_files == 3


# ---------------------------------------------------------------------------
# 3. Mixed case extension (.MD, .Md)
# ---------------------------------------------------------------------------


def test_mixed_case_md_extension():
    """.MD and .Md files are also converted (case-insensitive matching)."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), "UPPER.MD", "uppercase ext")
        _write(Path(src), "Mixed.Md", "mixed ext")

        result = convert_repository(src, out)

        assert result.md_converted == 2
        assert (Path(out) / "UPPER.txt").exists()
        assert (Path(out) / "Mixed.txt").exists()


# ---------------------------------------------------------------------------
# 4. Collision handling: file.md + file.txt → file.converted.txt
# ---------------------------------------------------------------------------


def test_collision_handling():
    """When file.txt already exists, the .md is saved as file.converted.txt."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), "notes.md", "markdown notes")
        _write(Path(src), "notes.txt", "existing txt")

        # Pre-populate output dir with the existing .txt so collision is triggered
        _write(Path(out), "notes.txt", "existing txt")

        result = convert_repository(src, out)

        converted = Path(out) / "notes.converted.txt"
        assert converted.exists(), "Expected notes.converted.txt due to collision"
        assert result.md_converted == 1


# ---------------------------------------------------------------------------
# 5. Non-md files are copied unchanged
# ---------------------------------------------------------------------------


def test_non_md_files_copied():
    """Text-based non-.md files are copied to the output unchanged."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        original = "x = 42\nprint(x)\n"
        _write(Path(src), "script.py", original)
        _write(Path(src), "config.yaml", "key: value\n")

        result = convert_repository(src, out)

        assert result.md_converted == 0
        assert (Path(out) / "script.py").read_text() == original
        assert (Path(out) / "config.yaml").read_text() == "key: value\n"


# ---------------------------------------------------------------------------
# 6. Binary files are skipped
# ---------------------------------------------------------------------------


def test_binary_files_are_skipped():
    """Binary files (containing null bytes) without .md extension are skipped."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        # Write a file with a null byte — heuristic binary detector will flag it
        _write(Path(src), "image.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        _write(Path(src), "readme.md", "text content")

        result = convert_repository(src, out)

        assert len(result.skipped) == 1
        assert "image.png" in result.skipped[0]
        assert not (Path(out) / "image.png").exists()
        assert result.md_converted == 1


# ---------------------------------------------------------------------------
# 7. Source directory is never modified
# ---------------------------------------------------------------------------


def test_source_directory_not_modified():
    """The source directory must remain identical after conversion."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), "doc.md", "# Doc")
        _write(Path(src), "helper.py", "pass")

        before = {
            str(p.relative_to(src)): p.read_text()
            for p in Path(src).rglob("*")
            if p.is_file()
        }

        convert_repository(src, out)

        after = {
            str(p.relative_to(src)): p.read_text()
            for p in Path(src).rglob("*")
            if p.is_file()
        }

        assert before == after, "Source directory was modified during conversion"


# ---------------------------------------------------------------------------
# 8. Empty source directory
# ---------------------------------------------------------------------------


def test_empty_source_directory():
    """An empty source directory produces an empty result with no errors."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        result = convert_repository(src, out)

        assert result.total_files == 0
        assert result.md_converted == 0
        assert result.errors == []
        assert result.skipped == []


# ---------------------------------------------------------------------------
# 9. Mapping entries are recorded for every file
# ---------------------------------------------------------------------------


def test_mappings_recorded():
    """All processed files appear in the mappings list with correct actions."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), "a.md", "md")
        _write(Path(src), "b.py", "py")
        _write(Path(src), "c.bin", b"\x00binary")

        result = convert_repository(src, out)

        actions = {m[0]: m[2] for m in result.mappings}
        assert actions.get("a.md") == "convert"
        assert actions.get("b.py") == "copy"
        assert actions.get("c.bin") == "skip"
