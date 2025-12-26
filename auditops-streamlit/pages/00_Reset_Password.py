"""
Reset Password Page (Not used with PIN-based authentication)
This page is kept for compatibility but is not needed with PIN-based login.
"""
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Reset Password",
    page_icon="🔑",
    layout="centered"
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
    .info-container {
        max-width: 500px;
        margin: 0 auto;
        padding: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="info-container">', unsafe_allow_html=True)
st.markdown('<h1 class="main-header">Password Reset</h1>', unsafe_allow_html=True)
st.markdown("---")

st.info("ℹ️ This application uses PIN-based authentication. Password reset is not applicable.")

st.markdown("### To change your PIN:")
st.markdown("""
1. Log in to the application with your current PIN
2. Go to the main page
3. Open the sidebar
4. Click on **"🔐 Change My PIN"**
5. Enter and confirm your new 4-digit PIN
""")

if st.button("Go to Login Page", use_container_width=True):
    st.switch_page("app.py")

st.markdown("</div>", unsafe_allow_html=True)
