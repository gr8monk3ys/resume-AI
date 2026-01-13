"""
Rate limiting utilities to prevent API abuse
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, Optional
import streamlit as st

class RateLimiter:
    """
    Simple rate limiter using session state.
    Tracks requests per user session to prevent abuse.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def _get_request_log(self) -> list:
        """Get request log from session state."""
        if 'rate_limit_log' not in st.session_state:
            st.session_state.rate_limit_log = []
        return st.session_state.rate_limit_log

    def _clean_old_requests(self, request_log: list) -> list:
        """Remove requests outside the current window."""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        return [ts for ts in request_log if ts > cutoff_time]

    def is_allowed(self, operation: str = "default") -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed under rate limit.

        Args:
            operation: Name of operation (for tracking different limits)

        Returns:
            (is_allowed, error_message)
        """
        # Get and clean request log
        request_log = self._get_request_log()
        request_log = self._clean_old_requests(request_log)

        # Check if under limit
        if len(request_log) >= self.max_requests:
            time_until_reset = int(self.window_seconds - (time.time() - min(request_log)))
            error_msg = (
                f"⏱️ Rate limit reached. You've made {len(request_log)} requests in the last "
                f"{self.window_seconds}s. Please wait {time_until_reset}s before trying again."
            )
            return False, error_msg

        # Allow request and log it
        request_log.append(time.time())
        st.session_state.rate_limit_log = request_log

        return True, None

    def get_remaining_requests(self) -> int:
        """Get number of remaining requests in current window."""
        request_log = self._get_request_log()
        request_log = self._clean_old_requests(request_log)
        return max(0, self.max_requests - len(request_log))

    def get_reset_time(self) -> int:
        """Get seconds until rate limit resets."""
        request_log = self._get_request_log()
        if not request_log:
            return 0

        request_log = self._clean_old_requests(request_log)
        if not request_log:
            return 0

        oldest_request = min(request_log)
        time_until_reset = int(self.window_seconds - (time.time() - oldest_request))
        return max(0, time_until_reset)

def check_rate_limit(
    max_requests: int = 20,
    window_seconds: int = 60,
    operation: str = "AI generation"
) -> bool:
    """
    Convenient function to check rate limit with default settings.

    Args:
        max_requests: Max requests per window
        window_seconds: Time window in seconds
        operation: Operation name for error message

    Returns:
        True if allowed, False if rate limited (shows error)
    """
    limiter = RateLimiter(max_requests, window_seconds)
    is_allowed, error_msg = limiter.is_allowed(operation)

    if not is_allowed:
        st.error(error_msg)
        st.info(f"💡 Remaining requests: {limiter.get_remaining_requests()}")
        return False

    # Show remaining requests in sidebar (non-intrusive)
    remaining = limiter.get_remaining_requests()
    if remaining <= 5:
        st.warning(f"⚠️ {remaining} requests remaining in the next minute")

    return True

# Pre-configured rate limiters for different operations
class RateLimiters:
    """Pre-configured rate limiters for different operations."""

    @staticmethod
    def ai_generation() -> RateLimiter:
        """Rate limiter for AI generation (expensive)."""
        try:
            from config import RATE_LIMIT_AI_CALLS, RATE_LIMIT_WINDOW
            return RateLimiter(RATE_LIMIT_AI_CALLS, RATE_LIMIT_WINDOW)
        except ImportError:
            return RateLimiter(20, 60)  # Default: 20 per minute

    @staticmethod
    def file_upload() -> RateLimiter:
        """Rate limiter for file uploads."""
        return RateLimiter(10, 60)  # 10 per minute

    @staticmethod
    def database_write() -> RateLimiter:
        """Rate limiter for database writes."""
        return RateLimiter(30, 60)  # 30 per minute

def show_rate_limit_info():
    """Display rate limit information in sidebar."""
    limiter = RateLimiters.ai_generation()
    remaining = limiter.get_remaining_requests()
    reset_time = limiter.get_reset_time()

    with st.sidebar:
        st.markdown("---")
        st.caption(f"🔒 API Requests: {remaining} remaining")
        if reset_time > 0 and remaining < 5:
            st.caption(f"⏱️ Resets in {reset_time}s")
