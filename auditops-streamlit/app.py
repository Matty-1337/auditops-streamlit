"""
AuditOps - Streamlit Operations Portal
Main application entry point with authentication and navigation.
"""
import streamlit as st
import streamlit.components.v1 as components
import requests
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


def show_auth_debug_panel():
    """Show auth persistence debug panel (safe - no secrets)."""
    with st.expander("🔍 Auth Persistence Debug", expanded=False):
        # Check localStorage presence via JS (set flag in session_state)
        if "ls_tokens_checked" not in st.session_state:
            components.html("""
                <script>
                (function() {
                    const hasAt = !!localStorage.getItem("auditops_at");
                    const hasRt = !!localStorage.getItem("auditops_rt");
                    const url = new URL(window.location.href);
                    url.searchParams.set('_ls_at', hasAt ? '1' : '0');
                    url.searchParams.set('_ls_rt', hasRt ? '1' : '0');
                    window.history.replaceState(null, '', url.toString());
                })();
                </script>
            """, height=0)
            st.session_state.ls_tokens_checked = True
            st.rerun()

        # Read localStorage flags from query params
        qp = dict(st.query_params)
        ls_at = qp.get("_ls_at") == "1"
        ls_rt = qp.get("_ls_rt") == "1"

        st.write(f"**localStorage auditops_at exists:** {'✅' if ls_at else '❌'}")
        st.write(f"**localStorage auditops_rt exists:** {'✅' if ls_rt else '❌'}")

        # Check query params
        has_access_token = "access_token" in qp
        has_refresh_token = "refresh_token" in qp
        has_restore_flag = "auditops_restore" in qp

        st.write(f"**Query param access_token present:** {'✅' if has_access_token else '❌'}")
        st.write(f"**Query param refresh_token present:** {'✅' if has_refresh_token else '❌'}")
        st.write(f"**Query param auditops_restore flag:** {'✅' if has_restore_flag else '❌'}")

        # Check Supabase session
        try:
            client = get_client(service_role=False)
            session = client.auth.get_session()
            has_session = session is not None
            st.write(f"**Supabase session exists:** {'✅' if has_session else '❌'}")
        except Exception as e:
            st.write(f"**Supabase session exists:** ❌ (error: {str(e)[:50]})")

        # Check Supabase user
        try:
            client = get_client(service_role=False)
            user_response = client.auth.get_user()
            user = user_response.user if hasattr(user_response, "user") else user_response
            if user and hasattr(user, "id"):
                user_id_preview = user.id[:8] + "..."
                st.write(f"**Supabase user exists:** ✅ (ID: {user_id_preview})")
            else:
                st.write("**Supabase user exists:** ❌")
        except Exception as e:
            st.write(f"**Supabase user exists:** ❌ (error: {str(e)[:50]})")

        # Check session state
        has_auth_user = "auth_user" in st.session_state
        has_auth_session = "auth_session" in st.session_state
        has_user_profile = "user_profile" in st.session_state

        st.write(f"**st.session_state.auth_user:** {'✅' if has_auth_user else '❌'}")
        st.write(f"**st.session_state.auth_session:** {'✅' if has_auth_session else '❌'}")
        st.write(f"**st.session_state.user_profile:** {'✅' if has_user_profile else '❌'}")

        # Show restore tracking
        restore_attempted = st.session_state.get("restore_attempted", False)
        restore_succeeded = st.session_state.get("restore_succeeded", False)

        st.write(f"**Restore attempted this session:** {'✅' if restore_attempted else '❌'}")
        st.write(f"**Restore succeeded this session:** {'✅' if restore_succeeded else '❌'}")


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
            # Clear any stale error messages from previous attempts
            if "last_login_error" in st.session_state:
                del st.session_state.last_login_error

            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Logging in..."):
                    from src.auth import login_with_password
                    import logging
                    import json
                    client = get_client(service_role=False)
                    ok, err = login_with_password(client, email, password)

                    if ok:
                        # CRITICAL: Store tokens in localStorage for refresh persistence
                        try:
                            session = client.auth.get_session()
                            logging.info("[AuditOps] Login successful, getting session...")

                            if not session:
                                logging.error("[AuditOps] get_session() returned None!")
                                st.error("Login succeeded but session not found. Please try again.")
                            else:
                                # Extract tokens
                                access_token = None
                                refresh_token = None

                                if hasattr(session, 'access_token'):
                                    access_token = session.access_token
                                elif isinstance(session, dict):
                                    access_token = session.get('access_token')

                                if hasattr(session, 'refresh_token'):
                                    refresh_token = session.refresh_token
                                elif isinstance(session, dict):
                                    refresh_token = session.get('refresh_token')

                                if not access_token or not refresh_token:
                                    logging.error(f"[AuditOps] Tokens missing! at={bool(access_token)} rt={bool(refresh_token)}")
                                    st.error("Login succeeded but tokens missing. Please try again.")
                                else:
                                    logging.info("[AuditOps] Tokens extracted, storing to localStorage...")

                                    # Use JSON encoding to safely pass tokens to JavaScript
                                    # This handles all special characters properly
                                    access_token_json = json.dumps(access_token)
                                    refresh_token_json = json.dumps(refresh_token)

                                    # Store tokens using st.markdown (more reliable than components.html)
                                    st.markdown(f"""
                                        <script>
                                        (function() {{
                                            try {{
                                                const at = {access_token_json};
                                                const rt = {refresh_token_json};
                                                localStorage.setItem("auditops_at", at);
                                                localStorage.setItem("auditops_rt", rt);
                                                console.log("[AuditOps] Tokens stored to localStorage");
                                            }} catch(e) {{
                                                console.error("[AuditOps] Failed to store tokens:", e);
                                            }}
                                        }})();
                                        </script>
                                    """, unsafe_allow_html=True)

                                    st.success("Login successful!")
                                    logging.info("[AuditOps] Rerunning after login...")

                                    # Small delay to ensure JS executes
                                    import time
                                    time.sleep(0.1)
                                    st.rerun()

                        except Exception as e:
                            logging.error(f"[AuditOps] Token storage exception: {str(e)[:200]}")
                            st.error(f"Login succeeded but token storage failed: {str(e)[:100]}")
                    else:
                        st.error(err if err else "Login failed. Please try again.")
    
    # Forgot Password button
    st.markdown("---")
    if st.button("Forgot password?", use_container_width=True):
        show_forgot_password()
    
    # Auth Persistence Debug
    show_auth_debug_panel()

    # Auth Triage expander
    with st.expander("🔍 Auth Triage", expanded=False):
        from src.config import get_supabase_url, get_supabase_key
        
        supabase_url = get_supabase_url()
        anon_key = get_supabase_key(service_role=False)
        
        # Extract hostname from URL (safe - no keys)
        if supabase_url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(supabase_url)
                hostname = parsed.hostname or "unknown"
            except Exception:
                hostname = "error"
        else:
            hostname = "not_set"
        
        st.write(f"**Supabase Host:** {hostname}")
        
        # Health check
        health_status = "unknown"
        if supabase_url and anon_key:
            try:
                health_url = f"{supabase_url}/auth/v1/health"
                headers = {
                    "apikey": anon_key,
                    "Authorization": f"Bearer {anon_key}"
                }
                response = requests.get(health_url, headers=headers, timeout=5)
                health_status = "✅ 200 OK" if response.status_code == 200 else f"❌ {response.status_code}"
            except Exception as e:
                health_status = f"❌ Error: {str(e)[:50]}"
        
        st.write(f"**Auth Health Check:** {health_status}")
        
        # Query params (keys only, no values)
        qp_keys = list(st.query_params.keys())
        st.write(f"**Query Params Keys:** {qp_keys if qp_keys else 'none'}")
        
        # Session check
        client = get_client(service_role=False)
        try:
            session = client.auth.get_session()
            has_session = session is not None
            st.write(f"**Session Exists:** {'✅ Yes' if has_session else '❌ No'}")
        except Exception:
            st.write("**Session Exists:** ❌ Error checking")
        
        # User check
        try:
            user_response = client.auth.get_user()
            user = user_response.user if hasattr(user_response, "user") else user_response
            if user and hasattr(user, "id"):
                user_id_preview = user.id[:8] + "..." if len(user.id) >= 8 else user.id
                st.write(f"**User Exists:** ✅ Yes (ID: {user_id_preview})")
            else:
                st.write("**User Exists:** ❌ No")
        except Exception:
            st.write("**User Exists:** ❌ Error checking")
    
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

    # Auth Persistence Debug (on main page too)
    show_auth_debug_panel()


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
                    # Redirect to reset password page - Supabase will append recovery tokens to this URL
                    # The Reset Password page (pages/00_Reset_Password.py) will handle the tokens
                    app_url = "https://auditops.streamlit.app"  # Streamlit Cloud URL
                    # Note: Supabase redirects to this base URL with tokens in fragment (#access_token=...)
                    # JavaScript in the app converts fragments to query params for Streamlit
                    
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
    import logging

    # STEP 0: Validate configuration first
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

    # STEP 1: CRITICAL - Always inject localStorage restore script at the VERY TOP
    # Use st.markdown for more reliable execution than components.html
    # This MUST run before any auth checks
    st.markdown("""
        <script>
        (function() {
            try {
                const currentUrl = new URL(window.location.href);
                const params = currentUrl.searchParams;

                // If we already processed restore, don't do it again
                if (params.has('auditops_restore')) {
                    console.log("[AuditOps] Already processed restore, skipping");
                    return;
                }

                // Check localStorage for tokens
                const access_token = localStorage.getItem("auditops_at");
                const refresh_token = localStorage.getItem("auditops_rt");

                if (access_token && refresh_token) {
                    console.log("[AuditOps] Tokens found in localStorage, redirecting to restore...");

                    // Add tokens and restore flag to URL
                    params.set('access_token', access_token);
                    params.set('refresh_token', refresh_token);
                    params.set('auditops_restore', '1');

                    // Redirect immediately
                    window.location.href = currentUrl.pathname + '?' + params.toString();
                } else {
                    console.log("[AuditOps] No tokens in localStorage");
                }
            } catch(e) {
                console.error("[AuditOps] localStorage restore error:", e);
            }
        })();
        </script>
    """, unsafe_allow_html=True)

    # STEP 2: Check if we have tokens in query params from the restore redirect
    query_params = dict(st.query_params)
    has_auditops_restore = query_params.get("auditops_restore") == "1"
    access_token = query_params.get("access_token")
    refresh_token = query_params.get("refresh_token")
    has_recovery_type = query_params.get("type") in ["recovery", "invite"]
    has_code = "code" in query_params

    # STEP 3: If this is a restore flow (not recovery/invite), consume tokens and restore session
    if has_auditops_restore and access_token and refresh_token and not has_recovery_type and not has_code:
        # Mark that we attempted restore
        if "restore_attempted" not in st.session_state:
            st.session_state.restore_attempted = True
            logging.info("[AuditOps] Processing token restore from localStorage...")

            try:
                client = get_client(service_role=False)

                # Set session using restored tokens
                try:
                    client.auth.set_session(access_token, refresh_token)
                    logging.info("[AuditOps] set_session() called successfully")
                except (TypeError, AttributeError):
                    # Fallback for older API versions
                    session_dict = {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_type": "bearer"
                    }
                    client.auth.set_session(session_dict)
                    logging.info("[AuditOps] set_session() with dict fallback")

                # Verify session is valid
                user_response = client.auth.get_user()
                user = user_response.user if hasattr(user_response, "user") else user_response

                if user and hasattr(user, "id"):
                    logging.info(f"[AuditOps] Session restored for user {user.id[:8]}...")

                    # Store in session_state
                    st.session_state.auth_user = user
                    if hasattr(user_response, 'session') and user_response.session:
                        st.session_state.auth_session = user_response.session

                    # Persist using helper
                    from src.supabase_client import persist_session
                    persist_session(client)

                    # Load user profile
                    from src.auth import load_user_profile
                    profile = load_user_profile(user.id, client=client)
                    if profile:
                        st.session_state.user_profile = profile

                    st.session_state.restore_succeeded = True
                    logging.info("[AuditOps] Restore succeeded, clearing URL params...")

                    # Clear query params and rerun
                    st.query_params.clear()
                    st.rerun()
                else:
                    # Invalid session
                    logging.warning("[AuditOps] Restore failed - invalid user")
                    st.session_state.restore_succeeded = False

                    # Clear bad tokens from localStorage
                    st.markdown("""
                        <script>
                        localStorage.removeItem("auditops_at");
                        localStorage.removeItem("auditops_rt");
                        console.log("[AuditOps] Cleared invalid tokens");
                        </script>
                    """, unsafe_allow_html=True)

                    st.query_params.clear()
                    st.rerun()

            except Exception as e:
                # Restore failed
                logging.error(f"[AuditOps] Restore exception: {str(e)[:200]}")
                st.session_state.restore_succeeded = False

                # Clear tokens
                st.markdown("""
                    <script>
                    localStorage.removeItem("auditops_at");
                    localStorage.removeItem("auditops_rt");
                    console.log("[AuditOps] Cleared tokens after error");
                    </script>
                """, unsafe_allow_html=True)

                st.query_params.clear()
                st.rerun()

    # STEP 4: Check for recovery/invite flows (password reset, etc.)
    if has_code or (access_token and refresh_token and not has_auditops_restore) or has_recovery_type:
        # Recovery/invite flow - let password reset page handle it
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

