"""
AuditOps - Streamlit Operations Portal
Main application entry point with authentication and navigation.
"""
import streamlit as st
from src.auth import login, logout, is_authenticated, get_current_profile, require_authentication
from src.config import ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR

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

