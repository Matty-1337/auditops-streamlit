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
    
    try:
        client = get_client(service_role=False)
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
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
            client = get_client(service_role=False)
        
        response = (
            client.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        
        # Handle response.data - could be a dict (single row) or list with one item
        profile_data = None
        if response.data:
            if isinstance(response.data, dict):
                profile_data = response.data
            elif isinstance(response.data, list) and len(response.data) > 0:
                profile_data = response.data[0]
            else:
                logging.warning(f"Unexpected response.data type: {type(response.data)} for user_id: {user_id[:8]}...")
        
        if profile_data:
            logging.info(f"Profile loaded successfully for user_id: {user_id[:8]}...")
            return profile_data
        
        # This shouldn't happen with .single() - it raises exception if not found
        logging.warning(f"Profile query returned no data for user_id: {user_id[:8]}...")
        return None
    except Exception as e:
        # .single() raises exception if no row found or RLS blocks access
        # Log diagnostic information for debugging
        error_msg = str(e)
        error_type = type(e).__name__
        
        # Check for RLS/permission errors specifically
        is_rls_error = (
            "permission denied" in error_msg.lower() or
            "42501" in error_msg or  # PostgreSQL permission denied error code
            "RLS" in error_msg.upper() or
            "policy" in error_msg.lower()
        )
        
        logging.error(
            f"Profile lookup failed for user_id: {user_id[:8]}... | "
            f"Error type: {error_type} | "
            f"Error: {error_msg[:200]} | "
            f"RLS/Permission issue: {is_rls_error} | "
            f"Query: profiles.select(*).eq(user_id, {user_id[:8]}...).single()"
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


def authenticate_with_tokens(access_token: str, refresh_token: str) -> dict | None:
    """
    Authenticate user with access and refresh tokens from magic link.
    
    Args:
        access_token: Access token from URL
        refresh_token: Refresh token from URL
    
    Returns:
        dict: User session data if successful, None otherwise
    """
    try:
        client = get_client(service_role=False)
        
        # CRITICAL FIX: supabase-py set_session takes access_token and refresh_token as separate parameters
        # Not a dict! This was the root cause of authentication failures.
        try:
            # Try the correct API signature: set_session(access_token, refresh_token)
            response = client.auth.set_session(access_token, refresh_token)
        except TypeError:
            # Fallback: some versions may accept a session dict, but this is deprecated
            # Log for debugging but don't expose to user
            import logging
            logging.warning("set_session dict format used - may be deprecated")
            session_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 3600
            }
            response = client.auth.set_session(session_data)
        except Exception as e:
            # If set_session fails completely, log and return None
            import logging
            logging.error(f"set_session failed: {str(e)}", exc_info=True)
            raise
        
        if response and hasattr(response, 'user') and response.user:
            # Store session in st.session_state
            st.session_state.auth_user = response.user
            if hasattr(response, 'session') and response.session:
                st.session_state.auth_session = response.session
            else:
                # Create minimal session object if not returned
                # Store tokens for rehydration on next run
                class Session:
                    def __init__(self, access_token, refresh_token):
                        self.access_token = access_token
                        self.refresh_token = refresh_token
                st.session_state.auth_session = Session(access_token, refresh_token)
            
            # CRITICAL: Verify session is actually set in the client
            # This ensures the client has the session for subsequent calls
            try:
                verify_response = client.auth.get_user()
                # Handle both response.user and direct user object
                verify_user = verify_response.user if hasattr(verify_response, "user") else verify_response
                if not verify_user or (hasattr(verify_user, "id") and not verify_user.id):
                    # Session set but not verified - this is a problem
                    import logging
                    logging.warning("set_session succeeded but get_user() returned no user")
            except Exception as e:
                import logging
                logging.warning(f"Session verification failed: {str(e)}")
                # Continue anyway - session might still be valid
            
            # Load user profile
            profile = load_user_profile(response.user.id)
            if profile:
                st.session_state.user_profile = profile
                return {
                    "user": response.user,
                    "session": st.session_state.auth_session,
                    "profile": profile
                }
            else:
                st.warning("⚠️ User profile not found. Please contact an administrator to create your profile.")
                return None
        
        return None
    except Exception as e:
        error_msg = str(e)
        # Log full error for debugging (not shown to user)
        import logging
        logging.error(f"Token authentication failed: {error_msg}", exc_info=True)
        
        # Don't expose token details in error messages
        if "Invalid" in error_msg or "expired" in error_msg.lower() or "token" in error_msg.lower():
            st.error("Authentication failed. The link may have expired. Please request a new magic link.")
        elif "set_session" in error_msg.lower() or "session" in error_msg.lower():
            st.error("Authentication failed. Please contact support if this issue persists.")
        else:
            st.error("Authentication failed. Please try again.")
        return None


def exchange_code_for_session(auth_code: str) -> dict | None:
    """
    Exchange PKCE authorization code for session tokens.
    
    Args:
        auth_code: Authorization code from PKCE flow
    
    Returns:
        dict: User session data if successful, None otherwise
    """
    try:
        client = get_client(service_role=False)
        
        # Try supabase-py method first (if it exists)
        try:
            if hasattr(client.auth, 'exchange_code_for_session'):
                response = client.auth.exchange_code_for_session(auth_code)
                if response and hasattr(response, 'user') and response.user:
                    # Store session
                    st.session_state.auth_user = response.user
                    if hasattr(response, 'session') and response.session:
                        st.session_state.auth_session = response.session
                    else:
                        # Create minimal session object
                        class Session:
                            def __init__(self, access_token, refresh_token):
                                self.access_token = access_token
                                self.refresh_token = refresh_token
                        # Extract tokens from response if available
                        if hasattr(response, 'access_token') and hasattr(response, 'refresh_token'):
                            st.session_state.auth_session = Session(response.access_token, response.refresh_token)
                        else:
                            # Fallback: we'll need to get tokens from direct API call
                            pass
                    
                    # Load user profile
                    profile = load_user_profile(response.user.id)
                    if profile:
                        st.session_state.user_profile = profile
                        return {
                            "user": response.user,
                            "session": st.session_state.auth_session,
                            "profile": profile
                        }
        except AttributeError:
            # Method doesn't exist, use direct HTTP call
            pass
        except Exception as e:
            import logging
            logging.warning(f"exchange_code_for_session method failed: {e}")
            # Fall through to direct HTTP call
        
        # Fallback: Direct HTTP call to Supabase token endpoint
        from src.config import get_supabase_url, get_supabase_key
        import requests
        
        supabase_url = get_supabase_url()
        supabase_key = get_supabase_key(service_role=False)
        
        # PKCE code exchange endpoint
        token_url = f"{supabase_url}/auth/v1/token?grant_type=authorization_code"
        
        headers = {
            "apikey": supabase_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # For PKCE, we need code_verifier, but Supabase magic links don't provide it
        # This is a limitation - PKCE requires code_verifier which must be stored from initial request
        # For now, try without code_verifier (may work for some Supabase configurations)
        data = {
            "code": auth_code,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            
            if "access_token" in token_data and "refresh_token" in token_data:
                # Use the tokens to set session
                return authenticate_with_tokens(
                    token_data["access_token"],
                    token_data["refresh_token"]
                )
            else:
                import logging
                logging.error(f"PKCE exchange response missing tokens: {token_data}")
                return None
        except requests.exceptions.RequestException as e:
            import logging
            logging.error(f"PKCE HTTP exchange failed: {e}", exc_info=True)
            return None
        
    except Exception as e:
        import logging
        logging.error(f"PKCE code exchange failed: {e}", exc_info=True)
        return None


def reset_password(new_password: str, access_token: str = None, refresh_token: str = None) -> bool:
    """
    Reset user password using recovery token.
    
    Args:
        new_password: New password to set
        access_token: Access token from recovery link (optional, uses current session if not provided)
        refresh_token: Refresh token from recovery link (optional, uses current session if not provided)
    
    Returns:
        bool: True if successful, False otherwise
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
                return True
            else:
                st.warning("⚠️ User profile not found. Please contact an administrator.")
                return False
        
        return False
    except Exception as e:
        error_msg = str(e)
        if "password" in error_msg.lower():
            st.error("Password reset failed. Please check password requirements and try again.")
        else:
            st.error("Password reset failed. Please try again.")
        return False