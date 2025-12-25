"""
Reset Password Page
Handles password recovery flow from Supabase recovery email links.
Supports both code-based (?code=...) and token-based (#access_token=...) recovery flows.
"""
import streamlit as st
import streamlit.components.v1 as components
import logging
import time
from src.supabase_client import get_client
from src.auth import establish_recovery_session, update_password

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

# JavaScript to convert URL fragments to query params (Streamlit cannot read fragments)
components.html("""
    <script>
    (function() {
        try {
            const hash = window.location.hash || "";
            if (!hash || hash.length < 2) return;
            
            const frag = hash.substring(1);
            const params = new URLSearchParams(frag);
            
            const hasAccessToken = params.has("access_token");
            const hasCode = params.has("code");
            const hasType = params.get("type") === "recovery" || params.has("refresh_token");
            
            if (!hasAccessToken && !hasCode && !hasType) return;
            
            const url = new URL(window.location.href);
            params.forEach((v, k) => url.searchParams.set(k, v));
            url.hash = "";
            window.location.replace(url.toString());
        } catch (e) {
            // fail silently
        }
    })();
    </script>
""", height=0)


def _safe_log_state(stage: str, qp: dict, session_present: bool):
    """Safe logging: never print token values."""
    logging.info(f"Reset Password {stage}: has_code={('code' in qp)}, has_access_token={('access_token' in qp)}, has_refresh_token={('refresh_token' in qp)}, has_type={('type' in qp)}, type_value={qp.get('type', None)}, session_present={session_present}")


def main():
    """Main page logic."""
    query_params = dict(st.query_params)
    
    # Safe logging
    _safe_log_state("entry", query_params, bool(st.session_state.get("recovery_session")))
    
    # If we have nothing useful and no session, attempt to convert fragment->query via JS
    if (
        "code" not in query_params
        and "access_token" not in query_params
        and "refresh_token" not in query_params
        and st.session_state.get("recovery_session") is None
    ):
        st.info("If you arrived from an email link, preparing your reset session…")
        time.sleep(0.2)
        st.rerun()
    
    # Try to establish a session once per visit
    established = False
    err_msg = None
    
    # If we already established a session earlier in this page lifecycle, reuse it
    if st.session_state.get("recovery_session"):
        established = True
        logging.info("Recovery session already established in this page lifecycle")
    else:
        try:
            # Try to establish recovery session (handles both code and token formats)
            established, err_msg = establish_recovery_session(query_params)
            if established:
                st.session_state["recovery_session"] = True
                logging.info("Recovery session established successfully")
        except Exception as e:
            err_msg = str(e)
            logging.error(f"Recovery session establishment exception: {err_msg[:200]}")
    
    # Safe logging (diagnostics)
    with st.expander("🔍 Diagnostics (safe)", expanded=False):
        _safe_log_state(
            "post-session-attempt",
            query_params,
            bool(st.session_state.get("recovery_session")),
        )
        if err_msg:
            st.write({"session_error": err_msg[:200]})  # Truncate to prevent secret leakage
    
    if not established:
        st.error("⚠️ Reset session not established. Please re-open the most recent reset email link.")
        st.info("Go to the login page and click 'Forgot Password?' to request a new reset link.")
        st.markdown("---")
        if st.button("Go to Login Page", use_container_width=True):
            # Clear all params
            for param in ["code", "access_token", "refresh_token", "type", "auth_pending", "error"]:
                if param in query_params:
                    del query_params[param]
            st.session_state.pop("recovery_session", None)
            st.rerun()
        st.stop()
        return
    
    # Now we have a session: render reset form
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Reset Password")
    st.markdown("---")
    st.success("✅ Reset session established. Please set a new password.")
    
    with st.form("reset_form", clear_on_submit=False):
        pw1 = st.text_input("New Password", type="password", placeholder="Enter your new password", help="Password must be at least 8 characters long")
        pw2 = st.text_input("Confirm New Password", type="password", placeholder="Confirm your new password")
        submit = st.form_submit_button("Set Password", type="primary", use_container_width=True)
    
    if submit:
        if not pw1 or not pw2:
            st.error("Please enter and confirm your new password.")
        elif pw1 != pw2:
            st.error("Passwords do not match.")
        elif len(pw1) < 8:
            st.error("Password must be at least 8 characters.")
        else:
            try:
                # Update password using the authenticated session
                success, error_msg = update_password(pw1)
                
                if success:
                    st.success("✅ Password updated successfully!")
                    st.info("You are now logged in. Redirecting...")
                    
                    # Clear recovery session marker
                    st.session_state.pop("recovery_session", None)
                    
                    # Clear URL params
                    for param in ["code", "access_token", "refresh_token", "type", "auth_pending"]:
                        if param in query_params:
                            del query_params[param]
                    
                    # Give user a moment to see success message
                    time.sleep(1)
                    
                    # Rerun will show main app (user is now authenticated)
                    st.rerun()
                else:
                    st.error(f"❌ {error_msg}")
                    
            except Exception as e:
                error_msg = str(e)
                logging.error(f"Password update exception: {error_msg[:200]}")
                st.error("Failed to update password. Please retry using a fresh reset link.")
    
    st.markdown("---")
    if st.button("Back to Login", use_container_width=True):
        # Clear all params
        for param in ["code", "access_token", "refresh_token", "type", "auth_pending", "error"]:
            if param in query_params:
                del query_params[param]
        st.session_state.pop("recovery_session", None)
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
