"""
Authentication and authorization helpers.
"""
import streamlit as st
from supabase import Client
from src.supabase_client import get_client, persist_session
from src.config import require_role, ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR


def login_with_password(client: Client, email: str, password: str) -> tuple[bool, str | None]:
    """
    Simple login function that authenticates and persists session.
    
    Args:
        client: Supabase client instance
        email: User email
        password: User password
    
    Returns:
        tuple: (ok: bool, err: str | None)
    """
    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response and hasattr(response, 'user') and response.user:
            # Persist session for rehydration on reruns
            persist_session(client)
            # Also store in legacy format for compatibility
            st.session_state.auth_user = response.user
            if hasattr(response, 'session') and response.session:
                st.session_state.auth_session = response.session
            return True, None
        else:
            return False, "Invalid email or password. Please try again."
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg or "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            return False, "Invalid email or password. Please try again."
        elif "Email not confirmed" in error_msg or "not confirmed" in error_msg.lower():
            return False, "Email not confirmed. Please check your email for a confirmation link."
        else:
            return False, "Login failed. Please try again."


def is_authed(client: Client) -> bool:
    """
    Check if client has a valid authenticated session.
    
    Args:
        client: Supabase client instance
    
    Returns:
        bool: True if authenticated, False otherwise
    """
    try:
        user_response = client.auth.get_user()
        user = user_response.user if hasattr(user_response, "user") else user_response
        return user is not None and hasattr(user, "id")
    except Exception:
        return False


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
            # Log auth response details
            logging.info(f"sign_in_with_password succeeded | user exists: True | user_id: {response.user.id[:8]}... | email: {response.user.email}")
            has_session = response.session is not None
            logging.info(f"sign_in_with_password response.session exists: {has_session}")
            
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
                            logging.info("Session explicitly set on client after sign_in_with_password")
                        except (TypeError, AttributeError):
                            # Fallback for different API versions
                            try:
                                session_dict = {
                                    "access_token": access_token,
                                    "refresh_token": refresh_token,
                                    "token_type": "bearer"
                                }
                                client.auth.set_session(session_dict)
                                logging.info("Session set on client using dict format (fallback)")
                            except Exception as e:
                                logging.warning(f"Failed to set session explicitly: {e}")
                    else:
                        logging.warning("Session tokens missing - cannot set session explicitly")
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
            logging.info(f"Attempting profile lookup for user_id: {response.user.id[:8]}... | using provided client with session")
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
    import streamlit.components.v1 as components

    try:
        client = get_client(service_role=False)
        client.auth.sign_out()
    except Exception:
        pass

    # Clear localStorage tokens
    components.html("""
        <script>
        (function() {
            try {
                localStorage.removeItem("auditops_at");
                localStorage.removeItem("auditops_rt");
            } catch(e) {
                console.error("Failed to clear tokens from localStorage:", e);
            }
        })();
        </script>
    """, height=0)

    # Clear session state
    for key in ["auth_user", "auth_session", "user_profile", "supabase_session"]:
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


def load_user_profile(user_id: str, client=None) -> dict | None:
    """
    Load user profile from database.
    
    Args:
        user_id: Supabase Auth user ID (UUID)
        client: Optional Supabase client instance (if provided, uses this instead of creating new)
    
    Returns:
        dict: Profile data or None if not found
    """
    import logging
    
    try:
        # Use provided client (with session) or get a new one
        if client is None:
            logging.info(f"load_user_profile: client not provided, getting new client (will rehydrate session if available)")
            client = get_client(service_role=False)
            # Log whether rehydration ran (check if get_client rehydrated)
            if "auth_session" in st.session_state and st.session_state.auth_session:
                logging.info(f"load_user_profile: session available in st.session_state, client should have rehydrated")
        else:
            logging.info(f"load_user_profile: using provided client instance (should have session)")
        
        # Use maybe_single() instead of single() to avoid exception if no row found
        # This is safer and allows us to check for None explicitly
        logging.info(f"Executing profile query: profiles.select(*).eq(user_id, {user_id[:8]}...).maybe_single()")
        response = (
            client.table("profiles")
            .select("*")
            .eq("user_id", user_id)  # CRITICAL: profiles table uses user_id, not id
            .maybe_single()
            .execute()
        )
        
        # Handle response.data - maybe_single() returns None if no row found, or dict if found
        profile_data = None
        if response.data:
            if isinstance(response.data, dict):
                profile_data = response.data
            elif isinstance(response.data, list) and len(response.data) > 0:
                profile_data = response.data[0]
            else:
                logging.warning(f"Unexpected response.data type: {type(response.data)} for user_id: {user_id[:8]}...")
        
        if profile_data:
            logging.info(f"Profile loaded successfully for user_id: {user_id[:8]}... | role: {profile_data.get('role', 'N/A')}")
            return profile_data
        
        # No profile found - this is expected if profile doesn't exist
        logging.warning(f"Profile query returned no data for user_id: {user_id[:8]}... | This may indicate profile row is missing or RLS is blocking")
        return None
    except Exception as e:
        # .maybe_single() should not raise exceptions, but handle any that occur
        # Log diagnostic information for debugging
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Extract error code/message/details if available
        error_code = None
        error_details = None
        if hasattr(e, 'code'):
            error_code = e.code
        if hasattr(e, 'message'):
            error_details = e.message
        elif hasattr(e, 'details'):
            error_details = e.details
        
        # Check for RLS/permission errors specifically
        is_rls_error = (
            "permission denied" in error_msg.lower() or
            "42501" in error_msg or
            (error_code and "42501" in str(error_code)) or
            "RLS" in error_msg.upper() or
            "policy" in error_msg.lower()
        )
        
        logging.error(
            f"Profile lookup EXCEPTION for user_id: {user_id[:8]}... | "
            f"Error type: {error_type} | "
            f"Error code: {error_code} | "
            f"Error message: {error_msg[:200]} | "
            f"Error details: {error_details[:200] if error_details else 'N/A'} | "
            f"RLS/Permission issue: {is_rls_error} | "
            f"Query: profiles.select(*).eq(user_id, {user_id[:8]}...).maybe_single()"
        )
        
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


def establish_recovery_session(query_params: dict) -> tuple[bool, str | None]:
    """
    Establish recovery session from query parameters.
    Handles both code-based (?code=...) and token-based (#access_token=...) flows.
    
    Args:
        query_params: Dictionary of query parameters from st.query_params
    
    Returns:
        tuple: (success: bool, error_message: str | None)
    """
    import logging
    
    try:
        client = get_client(service_role=False)
        
        # Try code-based flow first
        if "code" in query_params and query_params["code"]:
            code = query_params["code"]
            logging.info("Attempting code-based recovery session (exchange_code_for_session)")
            try:
                # Try dict-style first
                try:
                    response = client.auth.exchange_code_for_session({"auth_code": code})
                except TypeError:
                    # Fallback to positional argument
                    response = client.auth.exchange_code_for_session(code)
                
                # Verify session is valid
                user_response = client.auth.get_user()
                user = user_response.user if hasattr(user_response, "user") else user_response
                
                if user and hasattr(user, "id"):
                    # Store session in st.session_state
                    st.session_state.auth_user = user
                    if hasattr(response, 'session') and response.session:
                        st.session_state.auth_session = response.session
                    elif hasattr(user_response, 'session') and user_response.session:
                        st.session_state.auth_session = user_response.session
                    else:
                        # Create minimal session from tokens if needed
                        if hasattr(response, 'access_token') and hasattr(response, 'refresh_token'):
                            class Session:
                                def __init__(self, access_token, refresh_token):
                                    self.access_token = access_token
                                    self.refresh_token = refresh_token
                            st.session_state.auth_session = Session(response.access_token, response.refresh_token)
                    
                    logging.info(f"Code-based recovery session established for user_id: {user.id[:8]}...")
                    return True, None
                else:
                    return False, "Code exchange succeeded but no user returned"
                    
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Code-based recovery session failed: {error_msg[:200]}")
                return False, error_msg[:200]
        
        # Try token-based flow
        elif ("access_token" in query_params and query_params["access_token"]) and \
             ("refresh_token" in query_params and query_params["refresh_token"]):
            access_token = query_params["access_token"]
            refresh_token = query_params["refresh_token"]
            logging.info("Attempting token-based recovery session (set_session)")
            
            try:
                # Set session using recovery tokens
                try:
                    response = client.auth.set_session(access_token, refresh_token)
                except (TypeError, AttributeError):
                    # Fallback for older API versions
                    session_dict = {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_type": "bearer"
                    }
                    response = client.auth.set_session(session_dict)
                
                # Verify session is valid
                user_response = client.auth.get_user()
                user = user_response.user if hasattr(user_response, "user") else user_response
                
                if user and hasattr(user, "id"):
                    # Store session in st.session_state
                    st.session_state.auth_user = user
                    if hasattr(response, 'session') and response.session:
                        st.session_state.auth_session = response.session
                    elif hasattr(user_response, 'session') and user_response.session:
                        st.session_state.auth_session = user_response.session
                    
                    logging.info(f"Token-based recovery session established for user_id: {user.id[:8]}...")
                    return True, None
                else:
                    return False, "Session set but no user returned"
                    
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Token-based recovery session failed: {error_msg[:200]}")
                return False, error_msg[:200]
        
        else:
            return False, "No recovery code or tokens found in query parameters"
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Recovery session establishment exception: {error_msg[:200]}")
        return False, error_msg[:200]


def reset_password(new_password: str, access_token: str = None, refresh_token: str = None) -> tuple[bool, str]:
    """
    Reset user password using recovery token.
    
    Args:
        new_password: New password to set
        access_token: Access token from recovery link (optional, uses current session if not provided)
        refresh_token: Refresh token from recovery link (optional, uses current session if not provided)
    
    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        client = get_client(service_role=False)
        
        # If tokens provided, set session first (for recovery flow)
        # CRITICAL FIX: Use correct API signature
        if access_token and refresh_token:
            try:
                client.auth.set_session(access_token, refresh_token)
            except TypeError:
                # Fallback for older API versions
                session_data = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": 3600
                }
                client.auth.set_session(session_data)
            except Exception:
                # Session might already be set, continue anyway
                pass
        
        # Update user password
        response = client.auth.update_user({"password": new_password})
        
        if response.user:
            # After password reset, store the session
            st.session_state.auth_user = response.user
            if hasattr(response, 'session') and response.session:
                st.session_state.auth_session = response.session
            
            # Load user profile
            profile = load_user_profile(response.user.id)
            if profile:
                st.session_state.user_profile = profile
                return True, ""
            else:
                return False, "User profile not found. Please contact an administrator."
        
        return False, "Password reset failed. Please try again."
    except Exception as e:
        error_msg = str(e)
        if "password" in error_msg.lower():
            return False, "Password reset failed. Please check password requirements and try again."
        else:
            return False, "Password reset failed. Please try again."


def update_password(new_password: str) -> tuple[bool, str]:
    """
    Update user password using authenticated session.
    After successful update, user remains logged in.
    
    Args:
        new_password: New password to set
    
    Returns:
        tuple: (success: bool, error_message: str)
    """
    import logging
    
    try:
        client = get_client(service_role=False)
        
        # Verify we have a valid session
        try:
            user_response = client.auth.get_user()
            user = user_response.user if hasattr(user_response, "user") else user_response
            if not user or not hasattr(user, "id"):
                return False, "No authenticated session found. Please use the password reset link from your email."
        except Exception:
            return False, "Session expired. Please request a new password reset link."
        
        # Update password using supabase-py update_user method
        # Reference: https://supabase.com/docs/reference/python/auth-updateuser
        response = client.auth.update_user({"password": new_password})
        
        if response and hasattr(response, 'user') and response.user:
            # Update session state with new user object (password updated)
            st.session_state.auth_user = response.user
            if hasattr(response, 'session') and response.session:
                st.session_state.auth_session = response.session
            
            # Load user profile after password update
            profile = load_user_profile(response.user.id, client=client)
            if profile:
                st.session_state.user_profile = profile
            
            logging.info(f"Password updated successfully for user_id: {response.user.id[:8]}...")
            
            # Clear any stale error messages
            if "last_login_error" in st.session_state:
                del st.session_state.last_login_error
            
            return True, ""
        else:
            logging.warning("Password update returned no user")
            return False, "Password update failed. Please try again."
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Password update exception: {error_msg[:300]}")
        
        # Provide user-friendly error messages
        if "password" in error_msg.lower() and ("weak" in error_msg.lower() or "requirements" in error_msg.lower()):
            return False, "Password does not meet requirements. Please use a stronger password."
        elif "session" in error_msg.lower() or "token" in error_msg.lower() or "expired" in error_msg.lower():
            return False, "Session expired. Please request a new password reset link."
        else:
            return False, "Password update failed. Please try again or contact support."

