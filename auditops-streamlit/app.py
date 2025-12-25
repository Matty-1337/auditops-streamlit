"""
AuditOps - Streamlit Operations Portal
Main application entry point with authentication and navigation.
"""
import streamlit as st
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
                    if result:
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password. Please try again.")
    
    # Forgot Password button
    st.markdown("---")
    if st.button("Forgot password?", use_container_width=True):
        show_forgot_password()
    
    st.markdown("</div>", unsafe_allow_html=True)


def show_main_app():
    """Show main application with navigation."""
    profile = get_current_profile()
    if not profile:
        st.error("User profile not found. Please contact an administrator.")
        logout()
        st.rerun()
        return
    
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
    
    # Check authentication
    if not is_authenticated():
        show_login_page()
    else:
        show_main_app()


if __name__ == "__main__":
    main()

