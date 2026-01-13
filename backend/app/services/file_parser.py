"""
File parsing service for resume uploads.
Ported from Streamlit version to work with FastAPI.
"""
import io
from typing import Optional


def parse_txt(file_content: bytes) -> str:
    """Parse text file content."""
    try:
        return file_content.decode('utf-8')
    except UnicodeDecodeError:
        return file_content.decode('latin-1')


def parse_pdf(file_content: bytes) -> str:
    """Parse PDF file content."""
    try:
        import PyPDF2
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        text = []
        for page in pdf_reader.pages:
            text.append(page.extract_text())

        return '\n'.join(text)
    except ImportError:
        raise ImportError("PyPDF2 is required to parse PDF files. Install it with: pip install PyPDF2")
    except Exception as e:
        raise ValueError(f"Error parsing PDF file: {str(e)}")


def parse_docx(file_content: bytes) -> str:
    """Parse DOCX file content."""
    try:
        from docx import Document
        docx_file = io.BytesIO(file_content)
        doc = Document(docx_file)

        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)

        return '\n'.join(text)
    except ImportError:
        raise ImportError("python-docx is required to parse DOCX files. Install it with: pip install python-docx")
    except Exception as e:
        raise ValueError(f"Error parsing DOCX file: {str(e)}")


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
    """
    file_type = file_type.lower().strip('.')

    parsers = {
        'txt': parse_txt,
        'pdf': parse_pdf,
        'docx': parse_docx,
        'doc': parse_docx
    }

    parser = parsers.get(file_type)
    if not parser:
        raise ValueError(f"Unsupported file type: {file_type}. Supported types: {', '.join(parsers.keys())}")

    return parser(file_content)
