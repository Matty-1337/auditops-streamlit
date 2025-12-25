"""
AuditOps - Streamlit Operations Portal
Main application entry point with authentication and navigation.
"""
import streamlit as st
import streamlit.components.v1 as components
import os
from src.auth import (
    login, logout, is_authenticated, get_current_user, get_current_profile, 
    require_authentication, authenticate_with_tokens, reset_password,
    exchange_code_for_session, load_user_profile
)
from src.supabase_client import get_client
from src.config import ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR
from src.auth_instrumentation import (
    checkpoint_a_app_start, checkpoint_b_callback_detected,
    checkpoint_c_set_session_attempt, checkpoint_c_set_session_result,
    checkpoint_d_verify_user, checkpoint_e_gate_decision
)

# Page configuration
st.set_page_config(
    page_title="AuditOps",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# UX RACE FIX: Two-phase JavaScript execution to eliminate login flash
# Phase 1: Set auth_pending flag immediately if fragment exists (before Python runs)
# Phase 2: Convert fragment to query params and reload
components.html("""
    <script>
    (function() {
        const hash = window.location.hash && window.location.hash.length > 1 ? window.location.hash.substring(1) : '';
        const search = window.location.search;
        const hasTokenInQuery = search.includes('access_token') || search.includes('code');
        const hasAuthPending = search.includes('auth_pending=');
        
        // Phase 1: If fragment exists and no tokens in query yet, set auth_pending flag
        if (hash && !hasTokenInQuery && !hasAuthPending) {
            const params = new URLSearchParams(hash);
            const hasAccessToken = params.has('access_token');
            const hasCode = params.has('code');
            const hasError = params.has('error');
            
            // If fragment contains auth tokens/code/error, set auth_pending flag immediately
            if (hasAccessToken || hasCode || hasError) {
                const currentSearch = search || '';
                const separator = currentSearch ? '&' : '?';
                const newUrl = window.location.pathname + currentSearch + separator + 'auth_pending=1';
                window.location.replace(newUrl);
                return; // Exit early, page will reload with auth_pending=1
            }
        }
        
        // Phase 2: If auth_pending is set but tokens not yet in query, convert fragment now
        if (hasAuthPending && hash && !hasTokenInQuery) {
            const params = new URLSearchParams(hash);
            const accessToken = params.get('access_token');
            const refreshToken = params.get('refresh_token');
            const type = params.get('type');
            const code = params.get('code');
            const error = params.get('error');
            const errorDesc = params.get('error_description');
            
            if ((accessToken && refreshToken) || code || error) {
                // Build new URL with query params instead of hash
                const newParams = new URLSearchParams();
                if (accessToken && refreshToken) {
                    newParams.set('access_token', accessToken);
                    newParams.set('refresh_token', refreshToken);
                }
                if (code) {
                    newParams.set('code', code);
                }
                if (type) {
                    newParams.set('type', type);
                }
                if (error) {
                    newParams.set('error', error);
                    if (errorDesc) {
                        newParams.set('error_description', errorDesc);
                    }
                }
                // Keep auth_pending during conversion
                newParams.set('auth_pending', '1');
                
                // Replace URL (removing hash) and reload so server can read query params
                const newUrl = window.location.pathname + '?' + newParams.toString();
                window.history.replaceState(null, '', newUrl);
                window.location.reload();
            }
        }
    })();
    </script>
""", height=0)


def show_recovery_page(access_token: str, refresh_token: str):
    """Display password recovery/reset page."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Set New Password")
    st.markdown("---")
    st.info("Please enter your new password below.")
    
    with st.form("recovery_form"):
        new_password = st.text_input("New Password", type="password", placeholder="Enter your new password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your new password")
        submit = st.form_submit_button("Set New Password", type="primary", use_container_width=True)
        
        if submit:
            if not new_password or not confirm_password:
                st.error("Please enter and confirm your new password.")
            elif new_password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                with st.spinner("Setting new password..."):
                    if reset_password(new_password, access_token, refresh_token):
                        st.success("Password updated successfully! Redirecting...")
                        # Clear query params and rerun
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error("Failed to update password. Please try again.")
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_login_page():
    """Display password-first login page."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # Build stamp - visible truth test for deployment
    st.caption("Build: 8680c0f (expected)")
    
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Operations Portal")
    st.markdown("---")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Logging in..."):
                    result = login(email, password)
                    
                    # Use structured result to show correct error message
                    if result.get("ok"):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        # Show error based on structured result
                        if not result.get("auth_ok"):
                            # Auth failed
                            st.error(result.get("error", "Invalid email or password. Please try again."))
                        elif not result.get("profile_ok"):
                            # Auth succeeded but profile missing
                            st.warning(f"⚠️ {result.get('error', 'User profile not found. Please contact an administrator.')}")
                            # Still allow login - profile missing doesn't block auth
                            st.info("You are authenticated, but some features may be limited.")
                            st.rerun()
                        else:
                            # Shouldn't happen, but handle gracefully
                            st.error(result.get("error", "Login failed. Please try again."))
    
    # Optional: Forgot password button
    st.markdown("---")
    if st.button("Forgot Password?", use_container_width=True):
        show_forgot_password()
    
    # Auth debug accordion
    with st.expander("Auth debug", expanded=False):
        from src.config import get_supabase_url
        try:
            supabase_url = get_supabase_url()
            # Show only project ref (e.g., xxxxxx.supabase.co)
            if supabase_url:
                url_parts = supabase_url.replace("https://", "").replace("http://", "").split(".")
                if len(url_parts) > 1:
                    project_ref = url_parts[0] if url_parts[0] else "unknown"
                else:
                    project_ref = "unknown"
            else:
                project_ref = "not configured"
            st.write("Supabase project:", project_ref)
        except Exception:
            st.write("Supabase project: error reading config")
        
        # Check session state
        has_session = bool(st.session_state.get("auth_session"))
        st.write("Has session:", has_session)
        
        # Check user
        user = st.session_state.get("auth_user")
        if user and hasattr(user, "id"):
            user_id_preview = user.id[:8] if len(user.id) >= 8 else user.id
        else:
            user_id_preview = None
        st.write("User ID:", user_id_preview)
        
        # Check profile
        profile = st.session_state.get("user_profile")
        st.write("Profile exists:", bool(profile))
        
        # Last error (if stored)
        if "last_auth_error" in st.session_state:
            error_msg = str(st.session_state.last_auth_error)
            # Sanitize - show first 200 chars, redact tokens
            sanitized = error_msg[:200].replace("Bearer ", "Bearer [REDACTED]").replace("access_token", "[REDACTED]")
            st.write("Last error:", sanitized)
        else:
            st.write("Last error: none")
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_forgot_password():
    """Display forgot password form that sends reset email."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Reset Password")
    st.markdown("---")
    st.info("Enter your email address and we'll send you a password reset link.")
    
    with st.form("forgot_password_form"):
        email = st.text_input("Email", placeholder="your.email@example.com")
        submit = st.form_submit_button("Send Reset Link", type="primary", use_container_width=True)
        
        if submit:
            if not email:
                st.error("Please enter your email address.")
            else:
                try:
                    from src.config import get_supabase_url
                    client = get_client(service_role=False)
                    # Get app URL for redirect
                    supabase_url = get_supabase_url()
                    # Use Streamlit Cloud URL or construct from current request
                    app_url = "https://auditops.streamlit.app"  # Update if different
                    
                    client.auth.reset_password_for_email(
                        email,
                        options={"redirect_to": f"{app_url}"}
                    )
                    st.success(f"✅ Password reset link sent to {email}. Please check your email.")
                    st.info("💡 Note: You can also contact an administrator to reset your password.")
                except Exception as e:
                    error_msg = str(e)
                    if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                        st.error("Email address not found. Please contact an administrator.")
                    else:
                        st.error("Failed to send reset link. Please try again or contact support.")
    
    if st.button("Back to Login", use_container_width=True):
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_main_app():
    """Show main application with navigation."""
    profile = get_current_profile()
    if not profile:
        # Profile not found - show warning but DO NOT logout
        # User is authenticated, just missing profile data
        # Try to reload profile if we have a user
        user = get_current_user()
        if user and hasattr(user, "id"):
            import logging
            logging.warning(f"Profile missing in session state, attempting reload | user_id: {user.id[:8]}...")
            from src.auth import load_user_profile
            profile = load_user_profile(user.id)
            if profile:
                st.session_state.user_profile = profile
        
        if not profile:
            st.error("⚠️ User profile not found. Some features may be limited. Please contact an administrator.")
            # Use fallback values for display
            user = get_current_user()
            user_name = user.email if user and hasattr(user, "email") else "User"
            user_role = "UNKNOWN"
        else:
            user_name = profile.get("full_name", profile.get("email", "User"))
            user_role = profile.get("role", "UNKNOWN")
    else:
        user_name = profile.get("full_name", profile.get("email", "User"))
        user_role = profile.get("role", "UNKNOWN")
    
    user_name = profile.get("full_name", profile.get("email", "User"))
    user_role = profile.get("role", "UNKNOWN")
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"### 👤 {user_name}")
        st.markdown(f"**Role:** {user_role}")
        st.markdown("---")
        st.info("💡 Use the page selector above to navigate.")
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
    
    # Main content area
    st.markdown(f"# Welcome, {user_name}!")
    st.markdown(f"**Role:** {user_role}")
    st.markdown("---")
    st.info("👈 Use the sidebar to navigate to different sections.")


def should_show_auth_loading(query_params) -> bool:
    """
    Check if we should show loading screen instead of login UI.
    Returns True when auth_pending=1 is present but tokens/code not yet available.
    """
    auth_pending = query_params.get("auth_pending") == "1"
    has_tokens = query_params.get("access_token") is not None
    has_code = query_params.get("code") is not None
    has_error = query_params.get("error") is not None
    
    # Show loading if auth_pending is set but we don't have tokens/code/error yet
    return auth_pending and not has_tokens and not has_code and not has_error


def show_auth_loading():
    """Display loading screen during auth callback processing."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Signing you in...")
    st.markdown("---")
    with st.spinner("Processing authentication..."):
        st.info("Please wait while we complete your sign-in.")
    st.markdown("</div>", unsafe_allow_html=True)


def show_auth_error(error: str, error_description: str = None):
    """Display user-friendly error message for auth callback failures."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Authentication Error")
    st.markdown("---")
    
    # Sanitize error messages (don't expose raw error strings)
    if "expired" in error.lower() or "invalid" in error.lower():
        error_msg = "This sign-in link has expired or is invalid. Please request a new one."
    elif "denied" in error.lower() or "access_denied" in error.lower():
        error_msg = "Access was denied. Please contact support if you believe this is an error."
    else:
        error_msg = "An error occurred during sign-in. Please try again."
    
    st.error(f"⚠️ {error_msg}")
    
    if st.button("Try Again", type="primary", use_container_width=True):
        # Clear all auth-related query params
        params_to_clear = ["auth_pending", "error", "error_description", "access_token", "refresh_token", "code", "type"]
        for param in params_to_clear:
            if param in st.query_params:
                del st.query_params[param]
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    # CHECKPOINT A: App start - dump request/query context
    checkpoint_a_app_start()
    
    # Validate configuration first
    try:
        from src.config import validate_config
        validate_config()
    except ValueError as e:
        st.error(f"⚠️ Configuration Error: {str(e)}")
        st.info("💡 Please configure your Supabase credentials in `.streamlit/secrets.toml` or set environment variables.")
        st.stop()
        return
    except Exception as e:
        st.error(f"⚠️ Configuration Error: {str(e)}")
        st.stop()
        return
    
    # UX RACE FIX: Check for auth_pending loading state BEFORE any other logic
    # This prevents login UI flash - shows loading spinner instead
    # To debug: Set AUTH_DEBUG=1 in environment to see checkpoint information
    query_params = st.query_params
    if should_show_auth_loading(query_params):
        show_auth_loading()
        st.stop()
        return
    
    # Handle auth errors from callback
    error = query_params.get("error")
    error_description = query_params.get("error_description")
    if error and not is_authenticated():
        show_auth_error(error, error_description)
        st.stop()
        return
    
    # CRITICAL FIX: Rehydrate Supabase client session from st.session_state BEFORE checking auth
    # This ensures the client has the session even if it was lost between reruns
    # Note: get_client() now handles rehydration internally, but we verify here
    if "auth_session" in st.session_state and st.session_state.auth_session:
        try:
            client = get_client(service_role=False)  # This now rehydrates session internally
            # Verify the rehydrated session is valid
            try:
                # get_user() returns user object directly (not response.user)
                current_user_response = client.auth.get_user()
                # Handle both response.user and direct user object
                current_user = current_user_response.user if hasattr(current_user_response, "user") else current_user_response
                
                if current_user and hasattr(current_user, "id"):
                    # Session is valid, ensure st.session_state is in sync
                    if not st.session_state.get("auth_user") or \
                       getattr(st.session_state.get("auth_user"), "id", None) != current_user.id:
                        st.session_state.auth_user = current_user
                        if hasattr(current_user_response, "session"):
                            st.session_state.auth_session = current_user_response.session
            except Exception:
                # Session might be expired, clear it
                if "auth_user" in st.session_state:
                    del st.session_state.auth_user
                if "auth_session" in st.session_state:
                    del st.session_state.auth_session
        except Exception:
            pass  # Continue even if rehydration fails
    
    # DEPRIORITIZED: Handle password reset callback (from "Forgot Password" email)
    # This is optional - password reset emails may redirect here
    # Primary auth path is password login, not magic links
    access_token = query_params.get("access_token")
    refresh_token = query_params.get("refresh_token")
    auth_type = query_params.get("type")
    
    # Only handle recovery/password reset callbacks (not magic link login)
    if access_token and refresh_token and auth_type == "recovery" and not is_authenticated():
        # Password reset callback - show password reset form
        show_recovery_page(access_token, refresh_token)
        return
    
    # Note: Magic link login and PKCE flows are deprecated in favor of password-first auth
    # These are kept for backward compatibility but not the primary path
    
    # CHECKPOINT E: Gate logic - confirm authentication decision
    auth_status = is_authenticated()
    reason = "Session state check: " + (
        "auth_user exists" if "auth_user" in st.session_state and st.session_state.auth_user else "no auth_user"
    )
    checkpoint_e_gate_decision(auth_status, reason)
    
    # Check authentication
    if not auth_status:
        show_login_page()
    else:
        show_main_app()


if __name__ == "__main__":
    main()

