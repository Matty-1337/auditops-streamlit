"""
Client Registration Form
Allows new clients to register and request access to the system.
"""
import streamlit as st
from src.supabase_client import get_client
from datetime import datetime, timezone
import uuid

# Page config
st.set_page_config(page_title="Client Registration", page_icon="🏢", layout="centered")

st.title("🏢 Client Registration")
st.markdown("Register your business to work with our audit team.")
st.markdown("---")

with st.form("client_registration"):
    st.subheader("Business Information")

    # Required fields
    company_name = st.text_input("Company/Business Name *", placeholder="Acme Corporation")
    address = st.text_area("Business Address *", placeholder="123 Main St\nCity, State ZIP")

    # Contact information
    st.markdown("### Contact Information")
    contact_person = st.text_input("Contact Person Name *", placeholder="John Doe")
    contact_email = st.text_input("Contact Email *", placeholder="john@acmecorp.com")
    contact_phone = st.text_input("Contact Phone *", placeholder="(555) 123-4567")

    # Optional site information
    st.markdown("### Site Information (Optional)")
    st.caption("This information can be added later by administrators")
    wifi_name = st.text_input("WiFi Network Name", placeholder="AcmeCorp-Guest")
    wifi_password = st.text_input("WiFi Password", type="password", placeholder="Optional")

    # Site Access Codes
    st.markdown("### Site Access Codes (Optional)")
    col1, col2 = st.columns(2)
    with col1:
        alarm_code = st.text_input("Alarm Code", placeholder="1234", help="Numbers only")
        code_for_lights = st.text_input("Code for Lights", placeholder="5678", help="Numbers only")
    with col2:
        lockbox_code = st.text_input("Lock Box Code", placeholder="9012", help="Numbers only")
        cage_lock_code = st.text_input("CAGE LOCK/PAD LOCK", placeholder="3456", help="Numbers only")

    # Audit Day
    st.markdown("### Audit Schedule")
    audit_day = st.selectbox(
        "Audit Day",
        ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        help="Select the primary day for audits"
    )

    # Special Instructions
    special_instructions = st.text_area("Special Instructions/Notes",
                                       placeholder="Gate codes, parking info, check-in procedures, etc.")

    # Submit button
    submitted = st.form_submit_button("📤 Submit Registration", type="primary", use_container_width=True)

    if submitted:
        # Validation
        if not company_name or not address or not contact_person or not contact_email or not contact_phone:
            st.error("❌ Please fill in all required fields (marked with *)")
        elif "@" not in contact_email:
            st.error("❌ Please enter a valid email address")
        else:
            try:
                client = get_client(service_role=True)

                # Create client record with pending approval
                client_data = {
                    "client_id": str(uuid.uuid4()),
                    "client_name": company_name,
                    "address": address,
                    "contact_person": contact_person,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                    "wifi_name": wifi_name if wifi_name else None,
                    "wifi_password": wifi_password if wifi_password else None,
                    "alarm_code": alarm_code if alarm_code else None,
                    "lockbox_code": lockbox_code if lockbox_code else None,
                    "code_for_lights": code_for_lights if code_for_lights else None,
                    "cage_lock_code": cage_lock_code if cage_lock_code else None,
                    "audit_day": audit_day if audit_day else None,
                    "special_instructions": special_instructions if special_instructions else None,
                    "active": False,  # Not active until approved
                    "approval_status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat()
                }

                response = client.table("clients").insert(client_data).execute()

                if response.data:
                    st.success("✅ Registration submitted successfully!")
                    st.info("📧 Your registration is pending approval. We'll contact you at the email provided once approved.")
                    st.balloons()

                    # Show confirmation
                    with st.expander("📋 View Your Submission"):
                        st.write(f"**Company:** {company_name}")
                        st.write(f"**Contact:** {contact_person}")
                        st.write(f"**Email:** {contact_email}")
                        st.write(f"**Phone:** {contact_phone}")
                else:
                    st.error("❌ Registration failed. Please try again or contact support.")

            except Exception as e:
                st.error(f"❌ Error submitting registration: {str(e)}")
                st.info("Please contact support if this issue persists.")

st.markdown("---")
st.caption("Already registered? Contact your administrator to check your approval status.")
