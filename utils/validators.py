"""
Input validation utilities
"""

import re
from typing import Optional, Tuple

from config import MAX_FILE_SIZE_BYTES


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.

    Returns:
        (is_valid, error_message)
    """
    if not email:
        return True, None  # Empty is OK

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email):
        return True, None
    return False, "Invalid email format"


def validate_url(url: str, allow_empty: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format.

    Returns:
        (is_valid, error_message)
    """
    if not url:
        return (True, None) if allow_empty else (False, "URL cannot be empty")

    # Basic URL validation
    pattern = r"^https?://[^\s]+$"
    if re.match(pattern, url):
        return True, None
    return False, "Invalid URL format (must start with http:// or https://)"


def validate_file_size(file_obj) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file size.

    Returns:
        (is_valid, error_message)
    """
    if file_obj is None:
        return True, None

    try:
        file_size = len(file_obj.getvalue())
        if file_size > MAX_FILE_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
            return False, f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_mb}MB)"
        return True, None
    except Exception as e:
        return False, f"Error checking file size: {str(e)}"


def validate_linkedin_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate LinkedIn URL format."""
    if not url:
        return True, None

    if "linkedin.com/in/" in url or "linkedin.com/company/" in url:
        return validate_url(url, allow_empty=True)
    return False, "LinkedIn URL should contain 'linkedin.com/in/' or 'linkedin.com/company/'"


def validate_github_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate GitHub URL format."""
    if not url:
        return True, None

    if "github.com/" in url:
        return validate_url(url, allow_empty=True)
    return False, "GitHub URL should contain 'github.com/'"


def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input by removing potentially harmful characters.

    Args:
        text: Input text
        max_length: Maximum allowed length (optional)

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove null bytes and other control characters
    sanitized = text.replace("\x00", "").strip()

    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number format (loose validation).

    Returns:
        (is_valid, error_message)
    """
    if not phone:
        return True, None

    # Remove common formatting characters
    cleaned = re.sub(r"[\s\-\(\)\+\.]", "", phone)

    # Check if it's mostly digits (allow for country codes)
    if len(cleaned) >= 10 and cleaned.replace("+", "").isdigit():
        return True, None

    return False, "Phone number should contain at least 10 digits"


def validate_salary(salary: int) -> Tuple[bool, Optional[str]]:
    """Validate salary amount."""
    if salary < 0:
        return False, "Salary cannot be negative"
    if salary > 10_000_000:
        return False, "Salary seems unrealistically high"
    return True, None
