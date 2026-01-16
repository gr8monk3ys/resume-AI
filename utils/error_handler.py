"""
Centralized error handling for ResuBoost AI.

This module provides custom exception classes, error logging, and user-friendly
error message generation.
"""

import logging
import os
import traceback
from datetime import datetime
from typing import Optional, Tuple

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Create logger
logger = logging.getLogger("resuboost_ai")

# Only add handlers if they haven't been added yet (prevents duplicates on module reload)
if not logger.handlers:
    logger.setLevel(logging.INFO)

    # File handler for all logs
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f'app_{datetime.now().strftime("%Y%m%d")}.log')
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Error file handler for errors and above
    error_file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f'errors_{datetime.now().strftime("%Y%m%d")}.log')
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)
    logger.addHandler(error_file_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False


# Custom Exception Classes
class ResuBoostError(Exception):
    """Base exception for all ResuBoost AI errors."""

    def __init__(
        self, message: str, user_message: Optional[str] = None, details: Optional[dict] = None
    ):
        """
        Initialize ResuBoost error.

        Args:
            message: Technical error message for logging
            user_message: User-friendly error message to display
            details: Additional error details for logging
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An error occurred. Please try again."
        self.details = details or {}

    def log(self):
        """Log this error."""
        logger.error(f"{self.__class__.__name__}: {self.message}", extra=self.details)


class AuthenticationError(ResuBoostError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message, user_message="Invalid username or password. Please try again.", **kwargs
        )


class AuthorizationError(ResuBoostError):
    """Raised when user doesn't have permission."""

    def __init__(self, message: str = "Authorization failed", **kwargs):
        super().__init__(
            message, user_message="You don't have permission to perform this action.", **kwargs
        )


class ValidationError(ResuBoostError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            user_message=message,  # Validation errors are user-friendly
            details={"field": field} if field else {},
            **kwargs,
        )


class DatabaseError(ResuBoostError):
    """Raised when database operation fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="A database error occurred. Please try again or contact support.",
            **kwargs,
        )


class OpenAIError(ResuBoostError):
    """Raised when OpenAI API call fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="AI service is temporarily unavailable. Please try again later.",
            **kwargs,
        )


class FileProcessingError(ResuBoostError):
    """Raised when file processing fails."""

    def __init__(self, message: str, filename: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            user_message=f"Error processing file{': ' + filename if filename else ''}. Please check the file and try again.",
            details={"filename": filename} if filename else {},
            **kwargs,
        )


class RateLimitError(ResuBoostError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, wait_seconds: int = 0, **kwargs):
        super().__init__(
            message,
            user_message=(
                f"Too many attempts. Please wait {wait_seconds} seconds and try again."
                if wait_seconds
                else "Too many attempts. Please try again later."
            ),
            details={"wait_seconds": wait_seconds},
            **kwargs,
        )


# Error Handling Functions
def handle_exception(exc: Exception, context: str = "") -> Tuple[str, str]:
    """
    Handle exception and return user-friendly message.

    Args:
        exc: Exception that occurred
        context: Context where error occurred (for logging)

    Returns:
        Tuple of (user_message: str, log_message: str)

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     user_msg, log_msg = handle_exception(e, "Resume upload")
        ...     st.error(user_msg)
    """
    # Log the exception
    log_message = f"{context}: {str(exc)}\n{traceback.format_exc()}"

    # Handle custom exceptions
    if isinstance(exc, ResuBoostError):
        exc.log()
        return (exc.user_message, log_message)

    # Handle known third-party exceptions
    if "openai" in str(type(exc).__module__).lower():
        logger.error(f"OpenAI API Error in {context}: {str(exc)}")
        return ("AI service is temporarily unavailable. Please try again later.", log_message)

    if "sqlite3" in str(type(exc).__module__).lower():
        logger.error(f"Database Error in {context}: {str(exc)}")
        return ("A database error occurred. Please try again.", log_message)

    # Handle generic exceptions
    logger.error(log_message)
    return ("An unexpected error occurred. Please try again or contact support.", log_message)


def safe_execute(func, *args, context: str = "", default_return=None, **kwargs):
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        *args: Positional arguments for function
        context: Context description for logging
        default_return: Value to return if error occurs
        **kwargs: Keyword arguments for function

    Returns:
        Function result or default_return if error occurs

    Example:
        >>> result = safe_execute(
        ...     risky_function,
        ...     arg1, arg2,
        ...     context="Processing resume",
        ...     default_return=None
        ... )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        user_msg, _ = handle_exception(e, context)
        logger.error(f"Error in {context}: {str(e)}")
        return default_return


def log_error(message: str, exception: Optional[Exception] = None, **kwargs):
    """
    Log an error with additional context.

    Args:
        message: Error message
        exception: Optional exception object
        **kwargs: Additional context to log

    Example:
        >>> log_error(
        ...     "Failed to load user profile",
        ...     exception=e,
        ...     user_id=user['id'],
        ...     username=user['username']
        ... )
    """
    if exception:
        logger.error(f"{message}: {str(exception)}", exc_info=True, extra=kwargs)
    else:
        logger.error(message, extra=kwargs)


def log_warning(message: str, **kwargs):
    """
    Log a warning with additional context.

    Args:
        message: Warning message
        **kwargs: Additional context to log

    Example:
        >>> log_warning("Password strength below recommended", username="alice")
    """
    logger.warning(message, extra=kwargs)


def log_info(message: str, **kwargs):
    """
    Log an info message with additional context.

    Args:
        message: Info message
        **kwargs: Additional context to log

    Example:
        >>> log_info("User logged in successfully", user_id=123)
    """
    logger.info(message, extra=kwargs)


def get_user_friendly_message(error_type: str) -> str:
    """
    Get user-friendly error message for common error types.

    Args:
        error_type: Type of error (e.g., 'database', 'network', 'validation')

    Returns:
        User-friendly error message

    Example:
        >>> get_user_friendly_message('database')
        'A database error occurred. Please try again.'
    """
    messages = {
        "database": "A database error occurred. Please try again.",
        "network": "Network error. Please check your connection and try again.",
        "validation": "Please check your input and try again.",
        "authentication": "Invalid username or password.",
        "authorization": "You don't have permission to perform this action.",
        "rate_limit": "Too many attempts. Please wait and try again.",
        "file_upload": "Error uploading file. Please check the file and try again.",
        "ai_service": "AI service is temporarily unavailable. Please try again later.",
        "not_found": "The requested resource was not found.",
        "server_error": "An unexpected server error occurred. Please try again or contact support.",
    }

    return messages.get(error_type, "An error occurred. Please try again.")


def validate_and_execute(validation_func, execute_func, *args, **kwargs):
    """
    Validate input then execute function if validation passes.

    Args:
        validation_func: Function that returns (is_valid: bool, error_message: str)
        execute_func: Function to execute if validation passes
        *args: Arguments to pass to both functions
        **kwargs: Keyword arguments to pass to both functions

    Returns:
        Tuple of (success: bool, result_or_error: any)

    Example:
        >>> def validate_input(x):
        ...     return (x > 0, "Value must be positive")
        >>> def process_input(x):
        ...     return x * 2
        >>> success, result = validate_and_execute(validate_input, process_input, 5)
        >>> print(success, result)
        True 10
    """
    try:
        # Run validation
        is_valid, error_message = validation_func(*args, **kwargs)

        if not is_valid:
            raise ValidationError(error_message)

        # Execute main function
        result = execute_func(*args, **kwargs)
        return (True, result)

    except ResuBoostError as e:
        e.log()
        return (False, e.user_message)
    except Exception as e:
        user_msg, _ = handle_exception(e, "Validation and execution")
        return (False, user_msg)


# Error recovery functions
def retry_on_error(func, max_attempts: int = 3, delay: float = 1.0, *args, **kwargs):
    """
    Retry function on error with exponential backoff.

    Args:
        func: Function to execute
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (doubles each attempt)
        *args: Arguments to pass to function
        **kwargs: Keyword arguments to pass to function

    Returns:
        Function result or raises last exception

    Example:
        >>> result = retry_on_error(unstable_api_call, max_attempts=3, delay=1.0)
    """
    import time

    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                wait_time = delay * (2**attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_attempts} attempts failed: {str(e)}", exc_info=True)

    raise last_exception


def cleanup_old_logs(days: int = 30):
    """
    Clean up log files older than specified days.

    Args:
        days: Number of days to keep logs (default: 30)

    Example:
        >>> cleanup_old_logs(90)  # Keep 90 days of logs
    """
    import time
    from pathlib import Path

    cutoff_time = time.time() - (days * 24 * 60 * 60)

    for log_file in Path(LOG_DIR).glob("*.log"):
        if log_file.stat().st_mtime < cutoff_time:
            try:
                log_file.unlink()
                logger.info(f"Deleted old log file: {log_file.name}")
            except Exception as e:
                logger.error(f"Failed to delete log file {log_file.name}: {e}")


# Export all error handling utilities
__all__ = [
    # Exception classes
    "ResuBoostError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "DatabaseError",
    "OpenAIError",
    "FileProcessingError",
    "RateLimitError",
    # Error handling functions
    "handle_exception",
    "safe_execute",
    "log_error",
    "log_warning",
    "log_info",
    "get_user_friendly_message",
    "validate_and_execute",
    "retry_on_error",
    "cleanup_old_logs",
    # Logger
    "logger",
]
