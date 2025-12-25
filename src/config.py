"""
Configuration and constants for AuditOps.
Handles secrets management with fallback to environment variables.
"""
import os
import streamlit as st

# Role constants
ROLE_ADMIN = "ADMIN"
ROLE_MANAGER = "MANAGER"
ROLE_AUDITOR = "AUDITOR"

# Shift status constants
SHIFT_STATUS_DRAFT = "draft"
SHIFT_STATUS_SUBMITTED = "submitted"
SHIFT_STATUS_APPROVED = "approved"
SHIFT_STATUS_REJECTED = "rejected"

# Pay period status constants
PAY_PERIOD_OPEN = "open"
PAY_PERIOD_LOCKED = "locked"

# Access log action constants
ACTION_VIEW = "view"
ACTION_DOWNLOAD = "download"
ACTION_UPLOAD = "upload"


def get_supabase_url():
    """Get Supabase URL from secrets or environment."""
    try:
        return st.secrets["supabase"]["url"]
    except (KeyError, AttributeError):
        return os.getenv("SUPABASE_URL", "")


def get_supabase_key(service_role=False):
    """
    Get Supabase key from secrets or environment.
    
    Args:
        service_role: If True, return service_role key (admin access).
                     If False, return anon key (public access).
    
    Returns:
        str: The Supabase API key
    """
    try:
        if service_role:
            return st.secrets["supabase"]["service_role_key"]
        else:
            return st.secrets["supabase"]["anon_key"]
    except (KeyError, AttributeError):
        if service_role:
            return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        else:
            return os.getenv("SUPABASE_ANON_KEY", "")


def get_supabase_jwt_secret():
    """Get Supabase JWT secret for token verification."""
    try:
        return st.secrets["supabase"]["jwt_secret"]
    except (KeyError, AttributeError):
        return os.getenv("SUPABASE_JWT_SECRET", "")


def validate_config():
    """
    Validate that required configuration is present.
    Raises ValueError if critical config is missing.
    """
    url = get_supabase_url()
    anon_key = get_supabase_key(service_role=False)
    
    if not url:
        raise ValueError("SUPABASE_URL is required. Set it in .streamlit/secrets.toml or environment variable.")
    if not anon_key:
        raise ValueError("SUPABASE_ANON_KEY is required. Set it in .streamlit/secrets.toml or environment variable.")
    
    return True


def has_role(user_role, required_roles):
    """
    Check if user role matches any of the required roles.
    
    Args:
        user_role: The user's role (string or None)
        required_roles: Single role string or list of role strings
    
    Returns:
        bool: True if user has one of the required roles
    """
    if not user_role:
        return False
    
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    return user_role in required_roles


def require_role(required_roles):
    """
    Decorator/helper to check if user has required role.
    Use this in page functions to gate access.
    
    Args:
        required_roles: Single role string or list of role strings
    
    Returns:
        bool: True if access allowed, False otherwise
    """
    if "user_profile" not in st.session_state or not st.session_state.user_profile:
        return False
    
    user_role = st.session_state.user_profile.get("role")
    return has_role(user_role, required_roles)


# Backwards-compatible alias for existing page imports
require_role_access = require_role
