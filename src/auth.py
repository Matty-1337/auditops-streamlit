"""
Authentication and authorization helpers.
"""
import streamlit as st
from supabase import Client
from src.supabase_client import get_client
from src.config import require_role, ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR


def login(email: str, password: str) -> dict | None:
    """
    Authenticate user with Supabase Auth.
    
    Args:
        email: User email
        password: User password
    
    Returns:
        dict: User session data if successful, None otherwise
    """
    try:
        client = get_client(service_role=False)
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            # Store session
            st.session_state.auth_user = response.user
            st.session_state.auth_session = response.session
            
            # Load user profile
            profile = load_user_profile(response.user.id)
            if profile:
                st.session_state.user_profile = profile
                return {
                    "user": response.user,
                    "session": response.session,
                    "profile": profile
                }
            else:
                st.warning("⚠️ User profile not found. Please contact an administrator to create your profile.")
                return None
        
        return None
    except Exception as e:
        error_msg = str(e)
        # Provide more helpful error messages
        if "Invalid login credentials" in error_msg or "Email not confirmed" in error_msg:
            st.error("Invalid email or password. Please try again.")
        else:
            st.error(f"Login failed: {error_msg}")
        return None


def logout():
    """Log out current user and clear session."""
    try:
        client = get_client(service_role=False)
        client.auth.sign_out()
    except Exception:
        pass
    
    # Clear session state
    for key in ["auth_user", "auth_session", "user_profile"]:
        if key in st.session_state:
            del st.session_state[key]


def get_current_user():
    """Get current authenticated user from session state."""
    return st.session_state.get("auth_user")


def get_current_profile():
    """Get current user profile from session state."""
    return st.session_state.get("user_profile")


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return "auth_user" in st.session_state and st.session_state.auth_user is not None


def load_user_profile(user_id: str) -> dict | None:
    """
    Load user profile from database.
    
    Args:
        user_id: Supabase Auth user ID (UUID)
    
    Returns:
        dict: Profile data or None if not found
    """
    try:
        client = get_client(service_role=False)
        response = client.table("profiles").select("*").eq("id", user_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
    except Exception as e:
        # Don't show error to user here - let the caller handle it
        # This prevents showing errors during normal operation
        return None


def require_authentication():
    """
    Check if user is authenticated. Redirect to login if not.
    Returns True if authenticated, False otherwise.
    """
    if not is_authenticated():
        st.warning("Please log in to access this page.")
        st.stop()
        return False
    return True


def require_role_access(required_roles):
    """
    Check if user has required role. Show error and stop if not.
    
    Args:
        required_roles: Single role string or list of role strings
    """
    require_authentication()
    
    profile = get_current_profile()
    if not profile:
        st.error("User profile not found. Please contact an administrator.")
        st.stop()
        return
    
    user_role = profile.get("role")
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    if user_role not in required_roles:
        st.error(f"Access denied. This page requires one of these roles: {', '.join(required_roles)}")
        st.stop()


def get_user_role() -> str | None:
    """Get current user's role."""
    profile = get_current_profile()
    if profile:
        return profile.get("role")
    return None


def is_admin() -> bool:
    """Check if current user is an admin."""
    return get_user_role() == ROLE_ADMIN


def is_manager() -> bool:
    """Check if current user is a manager."""
    return get_user_role() == ROLE_MANAGER


def is_auditor() -> bool:
    """Check if current user is an auditor."""
    return get_user_role() == ROLE_AUDITOR

