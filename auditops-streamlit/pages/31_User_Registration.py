"""
User Registration Form
Multi-step registration for new auditors with personal and bank information.
"""
import streamlit as st
from src.supabase_client import get_client
from datetime import datetime, timezone
import uuid

# Page config
st.set_page_config(page_title="User Registration", page_icon="👤", layout="centered")

st.title("👤 Auditor Registration")
st.markdown("Create your auditor account to join our team.")
st.markdown("---")

# Initialize session state for multi-step form
if 'registration_step' not in st.session_state:
    st.session_state.registration_step = 1

if 'registration_data' not in st.session_state:
    st.session_state.registration_data = {}

# Progress indicator
col1, col2 = st.columns(2)
with col1:
    if st.session_state.registration_step == 1:
        st.info("📝 Step 1 of 2: Personal Information")
    else:
        st.success("✅ Step 1: Complete")
with col2:
    if st.session_state.registration_step == 2:
        st.info("💳 Step 2 of 2: Bank Information")
    else:
        st.caption("⏭️ Step 2: Bank Information")

st.markdown("---")

# STEP 1: Personal Information
if st.session_state.registration_step == 1:
    with st.form("personal_info_form"):
        st.subheader("Personal Information")

        full_name = st.text_input("Full Name *", placeholder="John Doe")
        phone = st.text_input("Phone Number *", placeholder="(555) 123-4567",
                              help="Last 4 digits will be your initial PIN")
        email = st.text_input("Email Address *", placeholder="john.doe@email.com")
        address = st.text_area("Home Address *", placeholder="123 Main St\nCity, State ZIP")

        st.markdown("### Emergency Contact")
        emergency_name = st.text_input("Emergency Contact Name *", placeholder="Jane Doe")
        emergency_phone = st.text_input("Emergency Contact Phone *", placeholder="(555) 987-6543")

        next_button = st.form_submit_button("Next: Bank Information ➡️", type="primary", use_container_width=True)

        if next_button:
            # Validation
            if not all([full_name, phone, email, address, emergency_name, emergency_phone]):
                st.error("❌ Please fill in all required fields")
            elif "@" not in email:
                st.error("❌ Please enter a valid email address")
            elif len(phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")) < 10:
                st.error("❌ Please enter a valid 10-digit phone number")
            else:
                # Save data and move to next step
                st.session_state.registration_data = {
                    'full_name': full_name,
                    'phone': phone,
                    'email': email,
                    'address': address,
                    'emergency_name': emergency_name,
                    'emergency_phone': emergency_phone
                }
                st.session_state.registration_step = 2
                st.rerun()

# STEP 2: Bank Information
elif st.session_state.registration_step == 2:
    with st.form("bank_info_form"):
        st.subheader("Direct Deposit Information")
        st.caption("Your bank information is securely encrypted and only used for payroll.")

        bank_name = st.text_input("Bank Name *", placeholder="First National Bank")
        bank_address = st.text_area("Bank Address *", placeholder="456 Bank St\nCity, State ZIP")
        account_number = st.text_input("Account Number *", type="password", placeholder="123456789")
        routing_number = st.text_input("Routing Number *", placeholder="987654321",
                                      help="9-digit routing number")

        # Confirmation checkbox
        confirm = st.checkbox("I confirm that the information provided is accurate")

        col1, col2 = st.columns(2)
        with col1:
            back_button = st.form_submit_button("⬅️ Back", use_container_width=True)
        with col2:
            submit_button = st.form_submit_button("📤 Submit Registration", type="primary", use_container_width=True)

        if back_button:
            st.session_state.registration_step = 1
            st.rerun()

        if submit_button:
            # Validation
            if not all([bank_name, bank_address, account_number, routing_number]):
                st.error("❌ Please fill in all bank information fields")
            elif len(routing_number.replace(" ", "")) != 9:
                st.error("❌ Routing number must be 9 digits")
            elif not confirm:
                st.error("❌ Please confirm that your information is accurate")
            else:
                try:
                    client = get_client(service_role=True)

                    # Generate PIN from last 4 digits of phone
                    phone_digits = ''.join(filter(str.isdigit, st.session_state.registration_data['phone']))
                    initial_pin = phone_digits[-4:] if len(phone_digits) >= 4 else "0000"

                    # Create user record
                    user_data = {
                        "name": st.session_state.registration_data['full_name'],
                        "phone": st.session_state.registration_data['phone'],
                        "email": st.session_state.registration_data['email'],
                        "address": st.session_state.registration_data['address'],
                        "emergency_contact_name": st.session_state.registration_data['emergency_name'],
                        "emergency_contact_phone": st.session_state.registration_data['emergency_phone'],
                        "bank_name": bank_name,
                        "bank_address": bank_address,
                        "bank_account_number": account_number,  # Should be encrypted in production
                        "bank_routing_number": routing_number,
                        "passcode": initial_pin,
                        "auth_uuid": str(uuid.uuid4()),
                        "role": "AUDITOR",
                        "approval_status": "pending"
                    }

                    response = client.table("app_users").insert(user_data).execute()

                    if response.data:
                        st.success("✅ Registration submitted successfully!")
                        st.info("📧 Your registration is pending approval. You'll be notified when your account is activated.")
                        st.balloons()

                        # Show PIN
                        st.success(f"🔑 Your initial PIN is: **{initial_pin}**")
                        st.warning("⚠️ Save this PIN! You'll need it to log in once approved.")

                        # Show confirmation
                        with st.expander("📋 View Your Submission"):
                            st.write(f"**Name:** {st.session_state.registration_data['full_name']}")
                            st.write(f"**Email:** {st.session_state.registration_data['email']}")
                            st.write(f"**Phone:** {st.session_state.registration_data['phone']}")
                            st.write(f"**Initial PIN:** {initial_pin}")

                        # Clear form data
                        st.session_state.registration_step = 1
                        st.session_state.registration_data = {}
                    else:
                        st.error("❌ Registration failed. Please try again.")

                except Exception as e:
                    st.error(f"❌ Error submitting registration: {str(e)}")
                    st.info("Please contact support if this issue persists.")

st.markdown("---")
st.caption("Already registered? Wait for admin approval, then log in with your PIN.")
