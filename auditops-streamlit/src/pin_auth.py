"""
Simple PIN-based authentication helpers for page access control.
"""
import streamlit as st
from src.config import ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR


def is_authenticated() -> bool:
    """Check if user is authenticated via PIN login."""
    return st.session_state.get('authenticated', False)


def get_current_user() -> dict | None:
    """Get current logged-in user data."""
    if is_authenticated():
        return st.session_state.get('user', None)
    return None


def get_user_role() -> str:
    """Get current user's role."""
    user = get_current_user()
    if user:
        return user.get('role', 'AUDITOR')
    return ''


def require_authentication():
    """
    Require user to be authenticated.
    If not authenticated, show login message and stop page execution.
    """
    if not is_authenticated():
        st.error("🔒 Please log in to access this page.")
        st.info("👈 Go back to the home page to log in.")
        if st.button("Go to Login Page"):
            st.switch_page("app.py")
        st.stop()


def require_role(allowed_roles: list[str] | str):
    """
    Require user to have one of the allowed roles.

    Args:
        allowed_roles: Single role string or list of allowed role strings

    Example:
        require_role(ROLE_ADMIN)  # Only admins
        require_role([ROLE_ADMIN, ROLE_MANAGER])  # Admins or managers
    """
    # First ensure user is authenticated
    require_authentication()

    # Normalize to list
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    user_role = get_user_role()

    # Check if user has required role
    if user_role not in allowed_roles:
        st.error(f"🚫 Access Denied: This page requires {' or '.join(allowed_roles)} role.")
        st.info(f"Your role: {user_role}")
        if st.button("Go Back to Home"):
            st.switch_page("app.py")
        st.stop()


def should_show_page(page_name: str, user_role: str = None) -> bool:
    """
    Determine if a page should be shown in navigation based on user role.

    Args:
        page_name: Name of the page file
        user_role: User's role (if None, uses current user's role)

    Returns:
        bool: True if page should be visible, False otherwise
    """
    if user_role is None:
        user_role = get_user_role()

    # Admin pages - only visible to admins
    admin_pages = [
        '10_Admin_Approvals.py',
        '11_Admin_Pay_Periods.py',
        '12_Admin_Clients.py',
        '13_Admin_Secrets_Access_Log.py',
        '99_Admin_Health_Check.py'
    ]

    if any(admin_page in page_name for admin_page in admin_pages):
        return user_role == ROLE_ADMIN

    # All other pages are visible to authenticated users
    return True
