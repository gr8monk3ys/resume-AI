"""
Input sanitization utilities for ResuBoost AI.

This module provides functions to sanitize and validate user inputs to prevent
security vulnerabilities like XSS, SQL injection, and malicious file uploads.
"""

import re
from typing import Optional, Tuple
import os


def sanitize_text_input(text: str, max_length: int = 1000, allow_html: bool = False) -> str:
    """
    Sanitize text input to prevent XSS and injection attacks.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length (default: 1000 characters)
        allow_html: Whether to allow HTML tags (default: False)

    Returns:
        Sanitized text string

    Example:
        >>> sanitize_text_input("<script>alert('xss')</script>Hello")
        "Hello"
        >>> sanitize_text_input("Normal text")
        "Normal text"
    """
    if not text:
        return ""

    # Limit length
    text = text[:max_length]

    # Remove HTML tags if not allowed
    if not allow_html:
        text = re.sub(r'<[^>]+>', '', text)

    # Remove null bytes
    text = text.replace('\x00', '')

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def sanitize_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and sanitize username.

    Rules:
    - 3-30 characters
    - Alphanumeric, underscore, hyphen only
    - Must start with letter
    - Case insensitive

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Example:
        >>> sanitize_username("john_doe")
        (True, None)
        >>> sanitize_username("12invalid")
        (False, "Username must start with a letter")
    """
    if not username:
        return (False, "Username cannot be empty")

    # Convert to lowercase for consistency
    username = username.lower().strip()

    # Length check
    if len(username) < 3:
        return (False, "Username must be at least 3 characters")
    if len(username) > 30:
        return (False, "Username must be less than 30 characters")

    # Pattern check (alphanumeric, underscore, hyphen)
    if not re.match(r'^[a-z][a-z0-9_-]*$', username):
        return (False, "Username must start with a letter and contain only letters, numbers, underscores, or hyphens")

    # Reserved usernames
    reserved = ['admin', 'root', 'system', 'api', 'test', 'demo', 'null', 'undefined']
    if username in reserved:
        return (False, "This username is reserved")

    return (True, None)


def sanitize_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and sanitize email address.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Example:
        >>> sanitize_email("user@example.com")
        (True, None)
        >>> sanitize_email("invalid.email")
        (False, "Invalid email format")
    """
    if not email:
        return (False, "Email cannot be empty")

    email = email.lower().strip()

    # Basic email pattern
    pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
    if not re.match(pattern, email):
        return (False, "Invalid email format")

    # Check length
    if len(email) > 254:  # RFC 5321
        return (False, "Email address too long")

    # Check for common typos
    common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    suspicious_patterns = [
        r'@gmial\.com$',  # Gmail typo
        r'@yahooo\.com$',  # Yahoo typo
        r'@outlok\.com$',  # Outlook typo
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, email):
            return (False, "Email domain appears to have a typo. Please double-check.")

    return (True, None)


def sanitize_filename(filename: str, allowed_extensions: Optional[list] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate and sanitize uploaded filename.

    Args:
        filename: Original filename
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.docx'])

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Example:
        >>> sanitize_filename("resume.pdf", ['.pdf', '.docx'])
        (True, None)
        >>> sanitize_filename("../../etc/passwd", ['.pdf'])
        (False, "Invalid filename characters")
    """
    if not filename:
        return (False, "Filename cannot be empty")

    # Remove path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return (False, "Invalid filename characters")

    # Check for null bytes
    if '\x00' in filename:
        return (False, "Invalid filename")

    # Get file extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    # Check allowed extensions
    if allowed_extensions:
        if ext not in allowed_extensions:
            return (False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")

    # Check filename length
    if len(filename) > 255:
        return (False, "Filename too long")

    # Check for executable extensions
    dangerous_extensions = ['.exe', '.bat', '.cmd', '.sh', '.py', '.js', '.vbs', '.scr']
    if ext in dangerous_extensions:
        return (False, "Executable files not allowed")

    return (True, None)


def sanitize_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL for job applications, LinkedIn, GitHub, etc.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Example:
        >>> sanitize_url("https://linkedin.com/in/johndoe")
        (True, None)
        >>> sanitize_url("javascript:alert('xss')")
        (False, "Invalid URL protocol")
    """
    if not url:
        return (True, None)  # URL is optional

    url = url.strip()

    # Check for dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    for protocol in dangerous_protocols:
        if url.lower().startswith(protocol):
            return (False, "Invalid URL protocol")

    # Must start with http:// or https://
    if not url.startswith(('http://', 'https://')):
        return (False, "URL must start with http:// or https://")

    # Basic URL pattern
    pattern = r'^https?://[a-z0-9.-]+\.[a-z]{2,}(/[^\s]*)?$'
    if not re.match(pattern, url, re.IGNORECASE):
        return (False, "Invalid URL format")

    # Check length
    if len(url) > 2000:
        return (False, "URL too long")

    return (True, None)


def sanitize_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate and sanitize phone number.

    Args:
        phone: Phone number to validate

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Example:
        >>> sanitize_phone("+1-555-123-4567")
        (True, None)
        >>> sanitize_phone("123")
        (False, "Phone number too short")
    """
    if not phone:
        return (True, None)  # Phone is optional

    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)

    # Allow + at start for international
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]

    # Should be numeric after cleaning
    if not cleaned.isdigit():
        return (False, "Phone number should contain only digits and standard separators")

    # Length check (minimum 7 digits, maximum 15 for international)
    if len(cleaned) < 7:
        return (False, "Phone number too short")
    if len(cleaned) > 15:
        return (False, "Phone number too long")

    return (True, None)


def sanitize_sql_like_pattern(pattern: str) -> str:
    """
    Escape special characters in SQL LIKE pattern to prevent SQL injection.

    Note: This is a defense-in-depth measure. Always use parameterized queries
    as the primary SQL injection prevention.

    Args:
        pattern: Search pattern for SQL LIKE clause

    Returns:
        Escaped pattern safe for SQL LIKE

    Example:
        >>> sanitize_sql_like_pattern("test%_")
        "test\\%\\_"
    """
    # Escape special LIKE characters
    pattern = pattern.replace('\\', '\\\\')  # Escape backslash first
    pattern = pattern.replace('%', '\\%')
    pattern = pattern.replace('_', '\\_')
    pattern = pattern.replace('[', '\\[')
    pattern = pattern.replace(']', '\\]')

    return pattern


def validate_json_field(data: str, max_size: int = 10000) -> Tuple[bool, Optional[str]]:
    """
    Validate JSON field for safe storage.

    Args:
        data: JSON string to validate
        max_size: Maximum size in bytes

    Returns:
        Tuple of (is_valid: bool, error_message: Optional[str])

    Example:
        >>> validate_json_field('{"key": "value"}')
        (True, None)
        >>> validate_json_field('{"key": "' + 'x' * 10001 + '"}')
        (False, "JSON data too large")
    """
    import json

    if not data:
        return (True, None)

    # Size check
    if len(data) > max_size:
        return (False, "JSON data too large")

    # Validate JSON format
    try:
        json.loads(data)
    except json.JSONDecodeError as e:
        return (False, f"Invalid JSON format: {str(e)}")

    return (True, None)


def sanitize_search_query(query: str, max_length: int = 200) -> str:
    """
    Sanitize search query to prevent injection attacks.

    Args:
        query: Search query string
        max_length: Maximum query length

    Returns:
        Sanitized query string

    Example:
        >>> sanitize_search_query("python developer")
        "python developer"
        >>> sanitize_search_query("<script>alert('xss')</script>")
        "alert('xss')"
    """
    if not query:
        return ""

    # Remove HTML tags
    query = re.sub(r'<[^>]+>', '', query)

    # Limit length
    query = query[:max_length]

    # Remove null bytes and control characters
    query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)

    # Strip whitespace
    query = query.strip()

    return query


# Comprehensive validation function for user profile updates
def validate_profile_update(data: dict) -> Tuple[bool, dict]:
    """
    Validate all fields in a profile update request.

    Args:
        data: Dictionary containing profile fields

    Returns:
        Tuple of (is_valid: bool, errors: dict)
        errors dict maps field names to error messages

    Example:
        >>> validate_profile_update({'email': 'invalid', 'phone': '123'})
        (False, {'email': 'Invalid email format', 'phone': 'Phone number too short'})
    """
    errors = {}

    # Validate email if provided
    if 'email' in data and data['email']:
        valid, error = sanitize_email(data['email'])
        if not valid:
            errors['email'] = error

    # Validate phone if provided
    if 'phone' in data and data['phone']:
        valid, error = sanitize_phone(data['phone'])
        if not valid:
            errors['phone'] = error

    # Validate URLs
    for field in ['linkedin', 'github', 'portfolio']:
        if field in data and data[field]:
            valid, error = sanitize_url(data[field])
            if not valid:
                errors[field] = error

    # Validate text fields
    text_fields = {
        'name': 100,
        'full_name': 100,
        'location': 100,
        'title': 100,
    }

    for field, max_len in text_fields.items():
        if field in data and data[field]:
            data[field] = sanitize_text_input(data[field], max_length=max_len)

    return (len(errors) == 0, errors)


# Export all sanitization functions
__all__ = [
    'sanitize_text_input',
    'sanitize_username',
    'sanitize_email',
    'sanitize_filename',
    'sanitize_url',
    'sanitize_phone',
    'sanitize_sql_like_pattern',
    'validate_json_field',
    'sanitize_search_query',
    'validate_profile_update',
]
