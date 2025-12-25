"""
Reset Password Page
Handles password recovery flow from Supabase recovery email links.

Supabase Dashboard Configuration Required:
- Site URL: https://auditops.streamlit.app
- Redirect URLs: https://auditops.streamlit.app/* (allows any path)

When user clicks password reset link in email:
1. Supabase redirects to: https://auditops.streamlit.app/#access_token=...&refresh_token=...&type=recovery
2. JavaScript converts URL fragment to query params (?access_token=...&refresh_token=...&type=recovery)
3. This page detects recovery tokens and shows password reset form
4. User enters new password
5. Password is updated via supabase.auth.update_user({"password": new_password})
6. User is logged out and redirected to login page
"""
import streamlit as st
import streamlit.components.v1 as components
import logging
from src.supabase_client import get_client
from src.auth import logout

# Page configuration
st.set_page_config(
    page_title="Reset Password",
    page_icon="🔑",
    layout="centered"
)

# Custom CSS matching login page
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

# UX RACE FIX: JavaScript to convert URL fragments to query params (same as main app)
# This ensures recovery tokens in fragments are accessible to Streamlit
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


def handle_recovery_tokens(access_token: str, refresh_token: str) -> bool:
    """
    Handle recovery tokens by setting session on Supabase client.
    
    Args:
        access_token: Access token from recovery link
        refresh_token: Refresh token from recovery link
    
    Returns:
        bool: True if session was successfully established, False otherwise
    """
    try:
        client = get_client(service_role=False)
        
        # Set session using recovery tokens
        # CRITICAL: Use correct API signature - access_token and refresh_token as separate params
        try:
            response = client.auth.set_session(access_token, refresh_token)
            logging.info("Recovery token session established successfully")
            
            # Verify session is valid by getting user
            user_response = client.auth.get_user()
            user = user_response.user if hasattr(user_response, "user") else user_response
            
            if user and hasattr(user, "id"):
                # Store session in st.session_state
                st.session_state.auth_user = user
                if hasattr(response, 'session') and response.session:
                    st.session_state.auth_session = response.session
                elif hasattr(user_response, 'session') and user_response.session:
                    st.session_state.auth_session = user_response.session
                
                logging.info(f"Recovery session verified for user_id: {user.id[:8]}...")
                return True
            else:
                logging.warning("Recovery token session established but no user returned")
                return False
                
        except (TypeError, AttributeError) as e:
            # Fallback for older API versions
            logging.warning(f"set_session API fallback attempted: {e}")
            try:
                session_dict = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer"
                }
                response = client.auth.set_session(session_dict)
                
                # Verify session
                user_response = client.auth.get_user()
                user = user_response.user if hasattr(user_response, "user") else user_response
                
                if user and hasattr(user, "id"):
                    st.session_state.auth_user = user
                    if hasattr(response, 'session') and response.session:
                        st.session_state.auth_session = response.session
                    logging.info(f"Recovery session established (fallback) for user_id: {user.id[:8]}...")
                    return True
                return False
            except Exception as fallback_error:
                logging.error(f"Recovery token session fallback failed: {fallback_error}")
                return False
        except Exception as e:
            logging.error(f"Recovery token session establishment failed: {e}")
            return False
            
    except Exception as e:
        logging.error(f"Failed to handle recovery tokens: {e}")
        return False


def update_password(new_password: str) -> tuple[bool, str]:
    """
    Update user password using authenticated session.
    
    Args:
        new_password: New password to set
    
    Returns:
        tuple: (success: bool, error_message: str)
    """
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
            logging.info(f"Password updated successfully for user_id: {response.user.id[:8]}...")
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


def show_reset_form():
    """Display password reset form."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Reset Password")
    st.markdown("---")
    st.info("Please enter your new password below.")
    
    with st.form("reset_password_form"):
        new_password = st.text_input(
            "New Password",
            type="password",
            placeholder="Enter your new password",
            help="Password must be at least 6 characters long"
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            placeholder="Confirm your new password"
        )
        submit = st.form_submit_button("Reset Password", type="primary", use_container_width=True)
        
        if submit:
            # Validation
            if not new_password or not confirm_password:
                st.error("Please enter and confirm your new password.")
            elif new_password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                # Update password
                with st.spinner("Resetting password..."):
                    success, error_msg = update_password(new_password)
                    
                    if success:
                        st.success("✅ Password reset successfully!")
                        st.info("You will be redirected to the login page. Please log in with your new password.")
                        
                        # Clear session and redirect to login
                        logout()
                        
                        # Wait a moment for user to see success message
                        import time
                        time.sleep(2)
                        
                        # Clear query params and redirect
                        query_params = st.query_params
                        for param in ["access_token", "refresh_token", "type", "auth_pending"]:
                            if param in query_params:
                                del query_params[param]
                        
                        st.rerun()
                    else:
                        st.error(f"❌ {error_msg}")
    
    st.markdown("---")
    if st.button("Back to Login", use_container_width=True):
        # Clear any query params
        query_params = st.query_params
        for param in ["access_token", "refresh_token", "type", "auth_pending"]:
            if param in query_params:
                del query_params[param]
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_no_token_error():
    """Display error when no recovery token is found."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Reset Password")
    st.markdown("---")
    
    st.error("⚠️ No password reset link detected.")
    st.info("""
    **To reset your password:**
    
    1. Go to the login page
    2. Click "Forgot Password?"
    3. Enter your email address
    4. Check your email for the reset link
    5. Click the link to reset your password
    """)
    
    st.markdown("---")
    if st.button("Go to Login Page", use_container_width=True):
        # Clear any query params
        query_params = st.query_params
        for param in ["access_token", "refresh_token", "type", "auth_pending", "error"]:
            if param in query_params:
                del query_params[param]
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_loading():
    """Display loading state while processing recovery tokens."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Reset Password")
    st.markdown("---")
    
    with st.spinner("Processing password reset link..."):
        st.info("Please wait while we verify your password reset link.")
    
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main page logic."""
    query_params = st.query_params
    
    # Check for auth_pending loading state (from JavaScript fragment conversion)
    auth_pending = query_params.get("auth_pending") == "1"
    has_tokens = query_params.get("access_token") is not None
    has_code = query_params.get("code") is not None
    
    if auth_pending and not has_tokens and not has_code:
        # Still waiting for fragment conversion
        show_loading()
        return
    
    # Check for error in query params
    error = query_params.get("error")
    if error:
        st.error(f"❌ Password reset error: {error}")
        error_desc = query_params.get("error_description")
        if error_desc:
            st.info(f"Details: {error_desc}")
        st.markdown("---")
        if st.button("Go to Login Page", use_container_width=True):
            # Clear error params
            for param in ["error", "error_description", "auth_pending"]:
                if param in query_params:
                    del query_params[param]
            st.rerun()
        return
    
    # Check for recovery tokens in query params
    access_token = query_params.get("access_token")
    refresh_token = query_params.get("refresh_token")
    auth_type = query_params.get("type")
    
    # Recovery flow: tokens present and type is recovery
    if access_token and refresh_token and auth_type == "recovery":
        logging.info("Recovery tokens detected in query params")
        
        # Try to establish session
        session_established = handle_recovery_tokens(access_token, refresh_token)
        
        if session_established:
            logging.info("Recovery session established - showing reset form")
            # Clear auth_pending param if present
            if "auth_pending" in query_params:
                del query_params.auth_pending
            show_reset_form()
        else:
            logging.error("Failed to establish recovery session")
            st.error("⚠️ Invalid or expired password reset link. Please request a new one.")
            st.info("Go to the login page and click 'Forgot Password?' to request a new reset link.")
            st.markdown("---")
            if st.button("Go to Login Page", use_container_width=True):
                # Clear all params
                for param in ["access_token", "refresh_token", "type", "auth_pending", "error"]:
                    if param in query_params:
                        del query_params[param]
                st.rerun()
    
    # Check if user already has a valid session (e.g., manually navigating here)
    elif "auth_user" in st.session_state and st.session_state.auth_user:
        # User has valid session - allow password reset
        logging.info("Valid session found - showing reset form")
        show_reset_form()
    
    else:
        # No tokens and no session - show error
        logging.warning("No recovery tokens or session found on reset password page")
        show_no_token_error()


if __name__ == "__main__":
    main()

