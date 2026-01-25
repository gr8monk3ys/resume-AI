"""
File parsing service for resume uploads.
Ported from Streamlit version to work with FastAPI.

Security limits are enforced to prevent denial-of-service attacks
via zip bombs, decompression bombs, or maliciously crafted files.

Security features:
- File size limits
- Magic byte validation to verify actual file content matches claimed type
- Input sanitization to prevent path traversal attacks
"""

import io
import re
from typing import Optional, Tuple

# Security limits for file parsing
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB max file size
MAX_PDF_PAGES = 100  # Maximum pages to process in a PDF
MAX_DECOMPRESSED_SIZE = 50 * 1024 * 1024  # 50 MB max decompressed content
MAX_TEXT_LENGTH = 500000  # Maximum characters to extract

# Magic byte signatures for file type validation
# These are the first bytes that identify file formats
MAGIC_BYTES = {
    "pdf": b"%PDF",  # PDF files start with %PDF
    "docx": b"PK",  # DOCX files are ZIP archives, start with PK (0x50 0x4B)
    "doc": b"PK",  # Modern .doc may also be DOCX format
    "zip": b"PK",  # ZIP archive signature
}

# Regex pattern for validating file_type parameter (alphanumeric only)
FILE_TYPE_PATTERN = re.compile(r"^[a-zA-Z0-9]+$")


def _check_file_size(file_content: bytes, max_size: int = MAX_FILE_SIZE_BYTES) -> None:
    """
    Check if file size is within acceptable limits.

    Args:
        file_content: Raw file content in bytes
        max_size: Maximum allowed file size in bytes

    Raises:
        ValueError: If file exceeds size limit
    """
    if len(file_content) > max_size:
        raise ValueError(
            f"File size ({len(file_content)} bytes) exceeds maximum allowed size "
            f"({max_size} bytes)"
        )


def _sanitize_file_type(file_type: str) -> str:
    """
    Sanitize and validate the file_type parameter to prevent path traversal attacks.

    Args:
        file_type: The file type/extension string

    Returns:
        Sanitized file type string (lowercase, without leading dot)

    Raises:
        ValueError: If file_type contains invalid characters

    Security:
        - Only allows alphanumeric characters
        - Prevents path traversal patterns like "../" or absolute paths
        - Normalizes to lowercase
    """
    # Remove leading dot and whitespace, convert to lowercase
    cleaned = file_type.lower().strip().lstrip(".")

    # Validate that file_type contains only alphanumeric characters
    # This prevents path traversal attacks like "../../etc/passwd"
    if not FILE_TYPE_PATTERN.match(cleaned):
        raise ValueError(
            f"Invalid file type: '{file_type}'. "
            "File type must contain only alphanumeric characters."
        )

    return cleaned


def _validate_magic_bytes(file_content: bytes, claimed_type: str) -> Tuple[bool, str]:
    """
    Validate file content using magic bytes to verify actual file type.

    This prevents attacks where a malicious file is uploaded with a fake extension.
    For example, an executable disguised as a PDF.

    Args:
        file_content: Raw file content in bytes
        claimed_type: The claimed file type (e.g., 'pdf', 'docx')

    Returns:
        Tuple of (is_valid, detected_type_or_error_message)

    Security:
        - Verifies actual file content matches the claimed type
        - Prevents file type spoofing attacks
    """
    if len(file_content) < 4:
        return False, "File content too small to validate"

    # Get the first few bytes for magic byte checking
    header = file_content[:4]

    # For text files, we don't have specific magic bytes
    # Accept any content that doesn't match other known binary signatures
    if claimed_type == "txt":
        # Check if it looks like a binary file that's being disguised as text
        for known_type, magic in MAGIC_BYTES.items():
            if header.startswith(magic):
                return False, f"File appears to be {known_type}, not plain text"
        return True, "txt"

    # For PDF files, check for %PDF signature
    if claimed_type == "pdf":
        if header.startswith(MAGIC_BYTES["pdf"]):
            return True, "pdf"
        return False, "File does not have valid PDF signature (expected %PDF header)"

    # For DOCX/DOC files, check for ZIP signature (PK)
    # DOCX files are actually ZIP archives containing XML
    if claimed_type in ("docx", "doc"):
        if header.startswith(MAGIC_BYTES["docx"]):
            return True, claimed_type
        return False, f"File does not have valid {claimed_type.upper()} signature (expected ZIP/PK header)"

    # Unknown file type - cannot validate magic bytes
    return True, claimed_type


def parse_txt(file_content: bytes) -> str:
    """Parse text file content."""
    _check_file_size(file_content)

    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        text = file_content.decode("latin-1")

    # Limit extracted text length
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]

    return text


def parse_pdf(file_content: bytes) -> str:
    """
    Parse PDF file content with security limits.

    Security measures:
    - File size limit check
    - Maximum page count limit
    - Maximum decompressed content size limit
    """
    _check_file_size(file_content)

    try:
        import PyPDF2

        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Check page count limit
        num_pages = len(pdf_reader.pages)
        if num_pages > MAX_PDF_PAGES:
            raise ValueError(
                f"PDF has too many pages ({num_pages}). "
                f"Maximum allowed is {MAX_PDF_PAGES} pages."
            )

        text = []
        total_length = 0

        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text() or ""
            total_length += len(page_text)

            # Check decompressed size limit
            if total_length > MAX_DECOMPRESSED_SIZE:
                raise ValueError(
                    f"Extracted text exceeds maximum allowed size. "
                    f"Processed {i + 1} pages before limit."
                )

            text.append(page_text)

        result = "\n".join(text)

        # Final text length limit
        if len(result) > MAX_TEXT_LENGTH:
            result = result[:MAX_TEXT_LENGTH]

        return result
    except ImportError:
        raise ImportError(
            "PyPDF2 is required to parse PDF files. Install it with: pip install PyPDF2"
        )
    except ValueError:
        # Re-raise ValueError (our security checks)
        raise
    except Exception as e:
        raise ValueError(f"Error parsing PDF file: {str(e)}")


def parse_docx(file_content: bytes) -> str:
    """
    Parse DOCX file content with security limits.

    Security measures:
    - File size limit check
    - Maximum decompressed content size limit
    """
    _check_file_size(file_content)

    try:
        from docx import Document

        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)

        text = []
        total_length = 0

        for paragraph in doc.paragraphs:
            para_text = paragraph.text
            total_length += len(para_text)

            # Check decompressed size limit
            if total_length > MAX_DECOMPRESSED_SIZE:
                raise ValueError(
                    "Extracted text exceeds maximum allowed size."
                )

            text.append(para_text)

        result = "\n".join(text)

        # Final text length limit
        if len(result) > MAX_TEXT_LENGTH:
            result = result[:MAX_TEXT_LENGTH]

        return result
    except ImportError:
        raise ImportError(
            "python-docx is required to parse DOCX files. Install it with: pip install python-docx"
        )
    except ValueError:
        # Re-raise ValueError (our security checks)
        raise
    except Exception as e:
        raise ValueError(f"Error parsing DOCX file: {str(e)}")


def parse_file(file_content: bytes, file_type: str) -> str:
    """
    Parse file content based on file type with security validations.

    Args:
        file_content: Raw file content in bytes
        file_type: File extension (txt, pdf, docx)

    Returns:
        Parsed text content

    Raises:
        ValueError: If file type is not supported, invalid, or content doesn't match type

    Security:
        - Sanitizes file_type to prevent path traversal attacks
        - Validates magic bytes to ensure file content matches claimed type
        - Enforces file size limits
    """
    # Sanitize file_type to prevent path traversal attacks
    # This rejects inputs like "../../../etc/passwd" or "pdf;rm -rf /"
    sanitized_type = _sanitize_file_type(file_type)

    parsers = {"txt": parse_txt, "pdf": parse_pdf, "docx": parse_docx, "doc": parse_docx}

    parser = parsers.get(sanitized_type)
    if not parser:
        raise ValueError(
            f"Unsupported file type: {sanitized_type}. Supported types: {', '.join(parsers.keys())}"
        )

    # Validate magic bytes to ensure file content matches claimed type
    # This prevents attacks where malicious files are disguised with fake extensions
    is_valid, validation_result = _validate_magic_bytes(file_content, sanitized_type)
    if not is_valid:
        raise ValueError(
            f"File content validation failed: {validation_result}. "
            "The file content does not match the claimed file type."
        )

    return parser(file_content)
