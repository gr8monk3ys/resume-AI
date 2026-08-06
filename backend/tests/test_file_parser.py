"""
Tests for the file parsing service.

Covers the security-critical, deterministic logic in
``app.services.file_parser``:

- File size limit enforcement
- file_type sanitization (path traversal / injection rejection)
- Magic byte validation (file-type spoofing prevention)
- parse_txt encoding handling and length truncation
- parse_file dispatch, including PDF and DOCX round-trips
- Error handling for unsupported / mismatched file types
"""

import io
import os
import sys

import pytest

# Ensure test env is set before app imports (mirrors conftest convention)
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.file_parser import (
    MAGIC_BYTES,
    MAX_FILE_SIZE_BYTES,
    MAX_TEXT_LENGTH,
    _check_file_size,
    _sanitize_file_type,
    _validate_magic_bytes,
    parse_docx,
    parse_file,
    parse_txt,
)

# =============================================================================
# _check_file_size
# =============================================================================


class TestCheckFileSize:
    def test_allows_content_within_limit(self):
        # Should not raise for small content.
        _check_file_size(b"hello world")

    def test_allows_content_at_exact_limit(self):
        _check_file_size(b"x" * MAX_FILE_SIZE_BYTES)

    def test_rejects_content_over_limit(self):
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            _check_file_size(b"x" * (MAX_FILE_SIZE_BYTES + 1))

    def test_respects_custom_max_size(self):
        with pytest.raises(ValueError):
            _check_file_size(b"abcdef", max_size=3)


# =============================================================================
# _sanitize_file_type
# =============================================================================


class TestSanitizeFileType:
    def test_strips_leading_dot_and_lowercases(self):
        assert _sanitize_file_type(".PDF") == "pdf"

    def test_strips_surrounding_whitespace(self):
        assert _sanitize_file_type("  DocX  ") == "docx"

    def test_accepts_alphanumeric(self):
        assert _sanitize_file_type("txt") == "txt"

    @pytest.mark.parametrize(
        "bad_input",
        [
            "../../../etc/passwd",
            "pdf;rm -rf /",
            "pdf/../secret",
            "file with space",
            "pdf.exe",
            "",
        ],
    )
    def test_rejects_path_traversal_and_injection(self, bad_input):
        with pytest.raises(ValueError, match="Invalid file type"):
            _sanitize_file_type(bad_input)


# =============================================================================
# _validate_magic_bytes
# =============================================================================


class TestValidateMagicBytes:
    def test_rejects_content_too_small(self):
        is_valid, msg = _validate_magic_bytes(b"ab", "txt")
        assert is_valid is False
        assert "too small" in msg

    def test_txt_accepts_plain_text(self):
        is_valid, detected = _validate_magic_bytes(b"just some resume text", "txt")
        assert is_valid is True
        assert detected == "txt"

    def test_txt_rejects_disguised_pdf(self):
        is_valid, msg = _validate_magic_bytes(MAGIC_BYTES["pdf"] + b"junk", "txt")
        assert is_valid is False
        assert "pdf" in msg

    def test_txt_rejects_disguised_zip(self):
        is_valid, msg = _validate_magic_bytes(MAGIC_BYTES["zip"] + b"junk", "txt")
        assert is_valid is False

    def test_pdf_accepts_valid_signature(self):
        is_valid, detected = _validate_magic_bytes(b"%PDF-1.7\n...", "pdf")
        assert is_valid is True
        assert detected == "pdf"

    def test_pdf_rejects_invalid_signature(self):
        is_valid, msg = _validate_magic_bytes(b"NOTPDF content", "pdf")
        assert is_valid is False
        assert "PDF signature" in msg

    def test_docx_accepts_zip_signature(self):
        is_valid, detected = _validate_magic_bytes(b"PK\x03\x04rest", "docx")
        assert is_valid is True
        assert detected == "docx"

    def test_doc_accepts_zip_signature(self):
        is_valid, detected = _validate_magic_bytes(b"PK\x03\x04rest", "doc")
        assert is_valid is True
        assert detected == "doc"

    def test_docx_rejects_non_zip(self):
        is_valid, msg = _validate_magic_bytes(b"%PDF-1.7 fake", "docx")
        assert is_valid is False
        assert "DOCX signature" in msg

    def test_unknown_type_passes_through(self):
        is_valid, detected = _validate_magic_bytes(b"arbitrary bytes", "rtf")
        assert is_valid is True
        assert detected == "rtf"


# =============================================================================
# parse_txt
# =============================================================================


class TestParseTxt:
    def test_parses_utf8(self):
        assert parse_txt("héllo wörld".encode("utf-8")) == "héllo wörld"

    def test_falls_back_to_latin1(self):
        # 0xe9 alone is invalid UTF-8 but is "é" in latin-1, forcing the
        # fallback decode path.
        result = parse_txt(b"caf\xe9")
        assert result == "café"

    def test_truncates_to_max_length(self):
        oversized = b"a" * (MAX_TEXT_LENGTH + 100)
        result = parse_txt(oversized)
        assert len(result) == MAX_TEXT_LENGTH

    def test_rejects_oversized_file(self):
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            parse_txt(b"x" * (MAX_FILE_SIZE_BYTES + 1))


# =============================================================================
# parse_docx (round-trip via python-docx)
# =============================================================================


def _build_docx_bytes(paragraphs):
    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class TestParseDocx:
    def test_extracts_paragraph_text(self):
        content = _build_docx_bytes(["First line", "Second line"])
        result = parse_docx(content)
        assert "First line" in result
        assert "Second line" in result

    def test_invalid_docx_raises_value_error(self):
        with pytest.raises(ValueError, match="Error parsing DOCX file"):
            parse_docx(b"PK\x03\x04 not a real docx archive body")


# =============================================================================
# parse_file (dispatch + validation integration)
# =============================================================================


class TestParseFile:
    def test_dispatches_txt(self):
        assert parse_file(b"plain resume content", "txt") == "plain resume content"

    def test_normalizes_extension_with_dot(self):
        assert parse_file(b"plain resume content", ".TXT") == "plain resume content"

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_file(b"some content here", "rtf")

    def test_path_traversal_type_rejected(self):
        with pytest.raises(ValueError, match="Invalid file type"):
            parse_file(b"some content here", "../../etc/passwd")

    def test_magic_byte_mismatch_rejected(self):
        # Claims pdf but content lacks the %PDF signature.
        with pytest.raises(ValueError, match="content validation failed"):
            parse_file(b"this is plain text not a pdf", "pdf")

    def test_docx_round_trip_through_dispatch(self):
        content = _build_docx_bytes(["Resume body paragraph"])
        result = parse_file(content, "docx")
        assert "Resume body paragraph" in result

    def test_doc_extension_uses_docx_parser(self):
        content = _build_docx_bytes(["Legacy doc paragraph"])
        result = parse_file(content, "doc")
        assert "Legacy doc paragraph" in result
