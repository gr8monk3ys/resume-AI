import io
from typing import Optional
from contextlib import contextmanager


@contextmanager
def _bytes_io_context(data: bytes):
    """Context manager for BytesIO to ensure proper cleanup."""
    buffer = io.BytesIO(data)
    try:
        yield buffer
    finally:
        buffer.close()


def parse_txt(file_content: bytes) -> str:
    """Parse text file content."""
    try:
        return file_content.decode('utf-8')
    except UnicodeDecodeError:
        return file_content.decode('latin-1')


def parse_pdf(file_content: bytes) -> str:
    """Parse PDF file content with proper resource cleanup."""
    try:
        import PyPDF2

        with _bytes_io_context(file_content) as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)

            return '\n'.join(text)
    except ImportError:
        raise ImportError("PyPDF2 is required to parse PDF files. Install it with: pip install PyPDF2")
    except Exception as e:
        raise ValueError(f"Error parsing PDF file: {str(e)}")


def parse_docx(file_content: bytes) -> str:
    """Parse DOCX file content with proper resource cleanup."""
    try:
        from docx import Document

        with _bytes_io_context(file_content) as docx_file:
            doc = Document(docx_file)

            text = []
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text.append(paragraph.text)

            return '\n'.join(text)
    except ImportError:
        raise ImportError("python-docx is required to parse DOCX files. Install it with: pip install python-docx")
    except Exception as e:
        raise ValueError(f"Error parsing DOCX file: {str(e)}")


# Supported file types and their parsers
# Note: .doc (legacy Word format) is NOT supported - python-docx only supports .docx
SUPPORTED_PARSERS = {
    'txt': parse_txt,
    'pdf': parse_pdf,
    'docx': parse_docx,
}


def parse_file(file_content: bytes, file_type: str) -> str:
    """
    Parse file content based on file type.

    Args:
        file_content: Raw file content in bytes
        file_type: File extension (txt, pdf, docx)

    Returns:
        Parsed text content

    Raises:
        ValueError: If file type is not supported

    Note:
        Legacy .doc files (Microsoft Word 97-2003) are NOT supported.
        Please convert to .docx format before uploading.
    """
    file_type = file_type.lower().strip('.')

    # Provide helpful error for legacy .doc files
    if file_type == 'doc':
        raise ValueError(
            "Legacy .doc format (Word 97-2003) is not supported. "
            "Please save your document as .docx (Word 2007+) and try again."
        )

    parser = SUPPORTED_PARSERS.get(file_type)
    if not parser:
        supported = ', '.join(SUPPORTED_PARSERS.keys())
        raise ValueError(f"Unsupported file type: {file_type}. Supported types: {supported}")

    return parser(file_content)

def extract_text_from_upload(uploaded_file, validate_size: bool = True) -> Optional[str]:
    """
    Extract text from a Streamlit uploaded file.

    Args:
        uploaded_file: Streamlit UploadedFile object
        validate_size: Whether to validate file size (default: True)

    Returns:
        Extracted text content or None if upload is None

    Raises:
        ValueError: If file is too large or invalid
    """
    if uploaded_file is None:
        return None

    file_content = uploaded_file.getvalue()

    # Validate file size if requested
    if validate_size:
        try:
            from config import MAX_FILE_SIZE_BYTES
            file_size = len(file_content)
            if file_size > MAX_FILE_SIZE_BYTES:
                size_mb = file_size / (1024 * 1024)
                max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
                raise ValueError(f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_mb}MB)")
        except ImportError:
            pass  # If config not available, skip validation

    file_extension = uploaded_file.name.split('.')[-1]

    return parse_file(file_content, file_extension)
