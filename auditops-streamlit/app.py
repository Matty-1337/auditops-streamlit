"""
AuditOps - Streamlit Operations Portal
Main application entry point with authentication and navigation.
"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone
from src.auth import login, logout, is_authenticated, get_current_profile, require_authentication
from src.config import ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR
from src.supabase_client import get_client

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


def show_login_page():
    """Display login page."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # BUILD MARKER: Visible deployment verification (DO NOT EDIT THIS MARKER - IT VERIFIES DEPLOYMENT)
    import subprocess
    import os
    try:
        # Get git commit SHA
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        git_sha = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=repo_root,
            stderr=subprocess.DEVNULL
        ).decode().strip()[:7]
    except:
        git_sha = "unknown"
    build_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    entrypoint_path = "auditops-streamlit/app.py"
    st.caption(f"🔧 BUILD: {git_sha} | {build_timestamp} | ENTRYPOINT: {entrypoint_path}")
    
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
                    
                    # CRITICAL: result is ALWAYS a dict with structured fields
                    # Never show multiple errors - use structured result to show ONLY the correct one
                    if not isinstance(result, dict):
                        # Fallback if result is not a dict (shouldn't happen)
                        st.error("Login failed. Please try again.")
                    elif result.get("ok"):
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        # Show ONLY ONE error based on structured result
                        error_msg = result.get("error", "Login failed. Please try again.")
                        
                        if not result.get("auth_ok"):
                            # Auth failed - show ONLY auth error
                            st.error(error_msg)
                        elif not result.get("profile_ok"):
                            # Auth succeeded but profile missing - show ONLY profile warning
                            st.warning(f"⚠️ {error_msg}")
                            # Still allow login - profile missing doesn't block auth
                            st.info("You are authenticated, but some features may be limited.")
                            st.rerun()
                        else:
                            # Shouldn't happen, but handle gracefully
                            st.error(error_msg)
    
    # Forgot Password button
    st.markdown("---")
    if st.button("Forgot password?", use_container_width=True):
        show_forgot_password()
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_main_app():
    """Show main application with navigation."""
    profile = get_current_profile()
    if not profile:
        # Profile not found - show warning but DO NOT logout
        # User is authenticated, just missing profile data
        # Try to reload profile if we have a user
        from src.auth import get_current_user, load_user_profile
        user = get_current_user()
        if user and hasattr(user, "id"):
            import logging
            logging.warning(f"Profile missing in session state, attempting reload | user_id: {user.id[:8]}...")
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
                    client = get_client(service_role=False)
                    # Get app URL for redirect
                    from src.config import get_supabase_url
                    app_url = "https://auditops.streamlit.app"  # Streamlit Cloud URL
                    
                    # Send password reset email
                    client.auth.reset_password_for_email(
                        email,
                        options={"redirect_to": app_url}
                    )
                    # Security: Always show same message to prevent email enumeration
                    st.success("✅ If the email exists, you'll receive a reset link.")
                    st.info("💡 Please check your email (including spam folder).")
                except Exception as e:
                    # Security: Never reveal whether email exists - always show generic message
                    st.success("✅ If the email exists, you'll receive a reset link.")
                    st.info("💡 Please check your email (including spam folder).")
    
    if st.button("Back to Login", use_container_width=True):
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main application entry point."""
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
    
    # Check authentication
    if not is_authenticated():
        show_login_page()
    else:
        show_main_app()


if __name__ == "__main__":
    main()

