"""
Authentication and authorization helpers.
"""
import streamlit as st
from supabase import Client
from src.supabase_client import get_client
from src.config import require_role, ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR


def login(email: str, password: str) -> dict:
    """
    Authenticate user with email and password (PRIMARY AUTH METHOD).
    
    Args:
        email: User email
        password: User password
    
    Returns:
        dict: Structured result with {
            "ok": bool,           # Overall success (auth_ok AND profile_ok)
            "auth_ok": bool,      # Authentication succeeded
            "profile_ok": bool,   # Profile lookup succeeded
            "error": str | None,  # Error message if any
            "user": User | None,  # User object if auth_ok
            "session": Session | None,  # Session if auth_ok
            "profile": dict | None  # Profile if profile_ok
        }
    """
    import logging
    
    # CRITICAL: Never show errors directly - always return structured result
    # This prevents multiple error messages from appearing
    
    try:
        client = get_client(service_role=False)
        
        # Attempt sign in - this can raise an exception on failure
        try:
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
        except Exception as auth_error:
            # Catch auth-specific errors and return structured result immediately
            error_msg = str(auth_error)
            error_type = type(auth_error).__name__
            logging.error(f"sign_in_with_password failed (type: {error_type}): {error_msg[:300]}")
            
            # Determine error message based on exception
            if "Invalid login credentials" in error_msg or "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
                error_text = "Invalid email or password. Please try again."
            elif "Email not confirmed" in error_msg or "not confirmed" in error_msg.lower():
                error_text = "Email not confirmed. Please check your email for a confirmation link."
            elif "email" in error_msg.lower() and ("not found" in error_msg.lower() or "does not exist" in error_msg.lower()):
                error_text = "Email address not found. Please contact an administrator."
            else:
                error_text = "Invalid email or password. Please try again."
            
            # Return immediately - do not continue
            return {
                "ok": False,
                "auth_ok": False,
                "profile_ok": False,
                "error": error_text,
                "user": None,
                "session": None,
                "profile": None
            }
        
        # Check if response has user (should always be present on success)
        if not hasattr(response, 'user') or response.user is None:
            logging.error("sign_in_with_password returned response without user object")
            return {
                "ok": False,
                "auth_ok": False,
                "profile_ok": False,
                "error": "Invalid email or password. Please try again.",
                "user": None,
                "session": None,
                "profile": None
            }
        
        # Auth succeeded - proceed with profile lookup
        if response.user:
            # Store session in st.session_state
            st.session_state.auth_user = response.user
            st.session_state.auth_session = response.session
            
            # CRITICAL: Ensure the client has the session from sign_in_with_password
            # The client should already have it, but explicitly set it to be sure
            if response.session:
                try:
                    # Extract tokens from session
                    access_token = None
                    refresh_token = None
                    
                    if hasattr(response.session, "access_token"):
                        access_token = response.session.access_token
                    elif isinstance(response.session, dict):
                        access_token = response.session.get("access_token")
                    
                    if hasattr(response.session, "refresh_token"):
                        refresh_token = response.session.refresh_token
                    elif isinstance(response.session, dict):
                        refresh_token = response.session.get("refresh_token")
                    
                    # Ensure client has the session set (may already be set by sign_in_with_password)
                    if access_token and refresh_token:
                        try:
                            client.auth.set_session(access_token, refresh_token)
                        except (TypeError, AttributeError):
                            # Fallback for different API versions
                            try:
                                session_dict = {
                                    "access_token": access_token,
                                    "refresh_token": refresh_token,
                                    "token_type": "bearer"
                                }
                                client.auth.set_session(session_dict)
                            except Exception as e:
                                logging.warning(f"Failed to set session explicitly: {e}")
                except Exception as e:
                    logging.warning(f"Session extraction/setting failed: {e}")
                    # Continue - client may already have session from sign_in_with_password
            
            # Verify session is valid
            try:
                verify_response = client.auth.get_user()
                verify_user = verify_response.user if hasattr(verify_response, "user") else verify_response
                if not verify_user or (hasattr(verify_user, "id") and verify_user.id != response.user.id):
                    logging.warning("Login succeeded but session verification failed")
            except Exception as e:
                logging.warning(f"Session verification failed: {e}")
                # Continue anyway - session might still be valid
            
            # Load user profile using the SAME client instance that has the session
            # Pass client explicitly to ensure session is used
            profile = load_user_profile(response.user.id, client=client)
            if profile:
                st.session_state.user_profile = profile
                return {
                    "ok": True,
                    "auth_ok": True,
                    "profile_ok": True,
                    "error": None,
                    "user": response.user,
                    "session": response.session,
                    "profile": profile
                }
            else:
                # Profile not found - auth succeeded but profile missing
                logging.warning(
                    f"Auth successful but profile not found | "
                    f"user_id: {response.user.id[:8]}... | "
                    f"email: {response.user.email}"
                )
                return {
                    "ok": False,  # Overall not ok because profile missing
                    "auth_ok": True,
                    "profile_ok": False,
                    "error": "User profile not found. Please contact an administrator to create your profile.",
                    "user": response.user,
                    "session": response.session,
                    "profile": None
                }
        
        # Auth failed - no user returned
        return {
            "ok": False,
            "auth_ok": False,
            "profile_ok": False,
            "error": "Invalid email or password. Please try again.",
            "user": None,
            "session": None,
            "profile": None
        }
    except Exception as e:
        error_msg = str(e)
        # Determine error message
        if "Invalid login credentials" in error_msg or "Email not confirmed" in error_msg:
            error_text = "Invalid email or password. Please try again."
        elif "email" in error_msg.lower() and "not found" in error_msg.lower():
            error_text = "Email address not found. Please contact an administrator."
        else:
            error_text = "Login failed. Please check your credentials and try again."
        
        logging.error(f"Login exception: {error_msg[:200]}")
        
        return {
            "ok": False,
            "auth_ok": False,
            "profile_ok": False,
            "error": error_text,
            "user": None,
            "session": None,
            "profile": None
        }


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

