"""
AuditOps - Streamlit Operations Portal
PIN-based authentication system
"""
import streamlit as st
from src.supabase_client import get_client
from src.config import validate_config

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


def login_with_pin(pin_code: str) -> tuple[bool, str, dict | None]:
    """
    Authenticate user with 4-digit PIN code.

    Simple PIN authentication using app_users table with integer IDs.

    Args:
        pin_code: The 4-digit PIN entered by user

    Returns:
        tuple: (success: bool, error_message: str, user_data: dict | None)
    """
    try:
        client = get_client(service_role=True)  # Use service role to bypass RLS

        # Query app_users table for matching passcode
        # Expected columns: id (integer), name, passcode, role
        response = client.table('app_users').select("*").eq('passcode', pin_code).execute()

        if response.data and len(response.data) > 0:
            # Found matching user
            user = response.data[0]
            return True, "", user
        else:
            # No matching passcode
            return False, "Invalid Code", None

    except Exception as e:
        return False, f"Login error: {str(e)}", None


def update_user_pin(user_id: int, new_pin: str) -> tuple[bool, str]:
    """
    Update user's PIN code.

    Args:
        user_id: The user's ID
        new_pin: The new 4-digit PIN

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        client = get_client(service_role=True)

        # Update the passcode
        response = client.table('app_users').update({
            'passcode': new_pin
        }).eq('id', user_id).execute()

        if response.data:
            return True, "PIN updated! Use this next time you log in."
        else:
            return False, "Failed to update PIN. Please try again."

    except Exception as e:
        return False, f"Error updating PIN: {str(e)}"


def show_login_page():
    """Display PIN-based login page."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">AuditOps</h1>', unsafe_allow_html=True)
    st.markdown("### Operations Portal")
    st.markdown("---")

    with st.form("login_form"):
        st.markdown("#### Enter your 4-digit Access Code")
        pin_code = st.text_input(
            "Access Code",
            type="password",
            max_chars=4,
            placeholder="****",
            help="Enter your 4-digit PIN"
        )
        submit = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submit:
            if not pin_code:
                st.error("Please enter your access code.")
            elif len(pin_code) != 4:
                st.error("Access code must be exactly 4 digits.")
            elif not pin_code.isdigit():
                st.error("Access code must contain only numbers.")
            else:
                with st.spinner("Logging in..."):
                    success, error_msg, user_data = login_with_pin(pin_code)

                    if success and user_data:
                        # Store user data in session state - simple integer ID
                        st.session_state.user = {
                            'id': user_data['id'],  # Integer ID from app_users
                            'name': user_data['name'],
                            'role': user_data.get('role', 'AUDITOR')  # Default to AUDITOR if no role
                        }
                        st.session_state.authenticated = True
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(error_msg)

    st.markdown("</div>", unsafe_allow_html=True)


def show_main_app():
    """Show main application with PIN change feature."""
    user = st.session_state.get('user', {})
    user_name = user.get('name', 'User')
    user_id = user.get('id')  # Integer ID from app_users
    user_role = user.get('role', 'AUDITOR')

    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"### 👤 {user_name}")
        st.markdown(f"**Role:** {user_role}")
        st.markdown("---")

        # Change PIN section
        with st.expander("🔐 Change My PIN", expanded=False):
            with st.form("change_pin_form"):
                new_pin = st.text_input(
                    "New 4-Digit PIN",
                    type="password",
                    max_chars=4,
                    placeholder="****",
                    help="Enter your new 4-digit PIN"
                )
                confirm_pin = st.text_input(
                    "Confirm New PIN",
                    type="password",
                    max_chars=4,
                    placeholder="****",
                    help="Re-enter your new PIN"
                )
                update_button = st.form_submit_button("Update PIN", use_container_width=True)

                if update_button:
                    if not new_pin or not confirm_pin:
                        st.error("Please enter both fields.")
                    elif len(new_pin) != 4:
                        st.error("PIN must be exactly 4 digits.")
                    elif not new_pin.isdigit():
                        st.error("PIN must contain only numbers.")
                    elif new_pin != confirm_pin:
                        st.error("PINs do not match. Please try again.")
                    else:
                        success, message = update_user_pin(user_id, new_pin)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

        st.markdown("---")
        st.info("💡 Use the page selector above to navigate.")
        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            if 'user' in st.session_state:
                del st.session_state.user
            if 'authenticated' in st.session_state:
                del st.session_state.authenticated
            st.rerun()

    # Main content area
    st.markdown(f"# Welcome, {user_name}!")
    st.markdown(f"**Role:** {user_role}")
    st.markdown("---")
    st.info("👈 Use the sidebar to navigate to different sections.")
    st.markdown("### Your Dashboard")
    st.write("This is your main application area. Navigate using the page selector in the sidebar above.")


def main():
    """Main application entry point."""

    # Validate configuration
    try:
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

    # Check if user is authenticated
    is_authenticated = st.session_state.get('authenticated', False)

    if not is_authenticated:
        show_login_page()
    else:
        show_main_app()


if __name__ == "__main__":
    main()
