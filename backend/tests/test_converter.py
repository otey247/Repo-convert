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
    """When both file.md and file.txt exist in the source, collision is handled."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        # Both files exist in the *source* repository.
        _write(Path(src), "notes.md", "markdown notes")
        _write(Path(src), "notes.txt", "existing txt")

        result = convert_repository(src, out)

        # Existing notes.txt from source must be preserved.
        existing_txt = Path(out) / "notes.txt"
        assert existing_txt.exists(), "Expected original notes.txt to be preserved"
        assert existing_txt.read_text() == "existing txt"

        # Converted Markdown should be written to notes.converted.txt due to collision.
        converted = Path(out) / "notes.converted.txt"
        assert converted.exists(), "Expected notes.converted.txt due to collision"
        assert converted.read_text() == "markdown notes"

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
# 6. Non-Markdown binary files are copied unchanged
# ---------------------------------------------------------------------------


def test_binary_non_markdown_files_are_copied():
    """Binary files without .md extension are copied in their original format."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        pdf_bytes = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\n\x00"
        docx_bytes = b"PK\x03\x04\x14\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        _write(Path(src), "files/report.pdf", pdf_bytes)
        _write(Path(src), "files/template.docx", docx_bytes)
        _write(Path(src), "readme.md", "text content")

        result = convert_repository(src, out)

        assert result.skipped == []
        assert (Path(out) / "files" / "report.pdf").read_bytes() == pdf_bytes
        assert (Path(out) / "files" / "template.docx").read_bytes() == docx_bytes
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
        assert actions.get("c.bin") == "copy"


# ---------------------------------------------------------------------------
# 10. .git directory is excluded
# ---------------------------------------------------------------------------


def test_git_directory_excluded():
    """Files inside .git/ are excluded from conversion and copy."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), ".git/config", "[core]\n\tbare = false")
        _write(Path(src), ".git/HEAD", "ref: refs/heads/main")
        _write(Path(src), "README.md", "# Readme")
        _write(Path(src), "src/main.py", "print('hello')")

        result = convert_repository(src, out)

        # .git files should be excluded entirely
        assert not (Path(out) / ".git").exists()
        assert result.total_files == 2  # README.md + src/main.py only
        assert result.md_converted == 1
        assert (Path(out) / "README.txt").exists()
        assert (Path(out) / "src" / "main.py").exists()


# ---------------------------------------------------------------------------
# 11. Binary .md files are skipped
# ---------------------------------------------------------------------------


def test_binary_md_file_skipped():
    """A .md file containing null bytes is treated as binary and skipped."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
        _write(Path(src), "binary.md", b"\x00\x01\x02 not real markdown")
        _write(Path(src), "good.md", "real markdown")

        result = convert_repository(src, out)

        assert result.md_converted == 1
        assert any("binary.md" in s for s in result.skipped)
        assert not (Path(out) / "binary.txt").exists()
        assert (Path(out) / "good.txt").exists()
