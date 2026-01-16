"""
UI helper functions for Streamlit
"""

from typing import Callable, Optional

import streamlit as st


def confirm_delete(
    item_name: str,
    item_id: str,
    on_confirm: Callable,
    button_label: str = "🗑️ Delete",
    confirm_label: str = "⚠️ Confirm Delete",
) -> bool:
    """
    Show a confirmation dialog for delete operations.

    Args:
        item_name: Name of item being deleted (for display)
        item_id: Unique ID for this delete operation
        on_confirm: Function to call when confirmed
        button_label: Label for initial delete button
        confirm_label: Label for confirmation button

    Returns:
        True if deleted, False otherwise
    """
    confirm_key = f"confirm_delete_{item_id}"

    # Check if we're in confirmation mode
    if st.session_state.get(confirm_key, False):
        st.warning(f"⚠️ Are you sure you want to delete '{item_name}'? This cannot be undone.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete", key=f"yes_{item_id}", type="primary"):
                on_confirm()
                st.session_state[confirm_key] = False
                return True

        with col2:
            if st.button("❌ Cancel", key=f"cancel_{item_id}"):
                st.session_state[confirm_key] = False
                st.rerun()

        return False
    else:
        # Show initial delete button
        if st.button(button_label, key=f"delete_{item_id}"):
            st.session_state[confirm_key] = True
            st.rerun()

        return False


def show_success(message: str, duration: int = 3):
    """
    Show a success message that persists across reruns.

    Args:
        message: Success message to display
        duration: How long to show (in page loads)
    """
    success_key = f"success_msg_{hash(message)}"

    if success_key not in st.session_state:
        st.session_state[success_key] = duration

    if st.session_state[success_key] > 0:
        st.success(message)
        st.session_state[success_key] -= 1
    else:
        if success_key in st.session_state:
            del st.session_state[success_key]


def show_error_with_suggestion(error: Exception, suggestions: Optional[list] = None):
    """
    Show user-friendly error message with suggestions.

    Args:
        error: The exception that occurred
        suggestions: List of suggestion strings to help user
    """
    error_str = str(error)

    # Map common errors to user-friendly messages
    error_messages = {
        "OPENAI_API_KEY": "🔑 OpenAI API key is missing or invalid. Please check your .env file.",
        "NoneType": "⚠️ Some required information is missing. Please fill in all required fields.",
        "connection": "🌐 Network error. Please check your internet connection.",
        "timeout": "⏱️ The operation took too long. Please try again.",
        "file": "📄 There was a problem with the file. Please try uploading a different file.",
        "too large": "📦 The file is too large. Maximum size is 10MB.",
    }

    # Find matching error message
    user_message = None
    for key, msg in error_messages.items():
        if key.lower() in error_str.lower():
            user_message = msg
            break

    if not user_message:
        user_message = f"⚠️ An error occurred: {error_str}"

    st.error(user_message)

    # Show suggestions if provided
    if suggestions:
        st.info("💡 **Try this:**\n" + "\n".join(f"- {s}" for s in suggestions))

    # Show technical details in expander
    with st.expander("🔧 Technical Details"):
        st.code(f"{type(error).__name__}: {error_str}")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "2.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def show_loading(message: str = "Processing..."):
    """
    Context manager for showing loading spinner.

    Usage:
        with show_loading("Generating cover letter..."):
            result = generate_letter()
    """
    return st.spinner(message)
