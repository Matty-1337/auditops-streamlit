"""
Admin User Approvals
Review and approve/reject pending user registrations.
"""
import streamlit as st
from src.pin_auth import require_authentication, require_role, get_current_user
from src.config import ROLE_ADMIN
from src.supabase_client import get_client
from datetime import datetime, timezone

# Page config
st.set_page_config(page_title="User Approvals", layout="wide")

# Authentication
require_authentication()
require_role(ROLE_ADMIN)

user = get_current_user()
admin_id = user.get('id')

st.title("👤 User Registration Approvals")
st.markdown("Review and approve pending auditor registrations.")
st.markdown("---")

# Get pending users
client = get_client(service_role=True)
response = client.table("app_users").select("*").eq("approval_status", "pending").execute()
pending_users = response.data or []

if not pending_users:
    st.success("✅ No pending user approvals!")
    st.info("New user registrations will appear here for review.")
else:
    st.metric("Pending Approvals", len(pending_users))

    for idx, user_record in enumerate(pending_users):
        with st.expander(f"👤 {user_record['name']}", expanded=True):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"### {user_record['name']}")

                st.markdown("**Contact Information:**")
                st.write(f"📧 {user_record.get('email', 'N/A')}")
                st.write(f"📞 {user_record.get('phone', 'N/A')}")
                st.write(f"🏠 {user_record.get('address', 'N/A')}")

                st.markdown("---")
                st.markdown("**Emergency Contact:**")
                st.write(f"👤 {user_record.get('emergency_contact_name', 'N/A')}")
                st.write(f"📞 {user_record.get('emergency_contact_phone', 'N/A')}")

                st.markdown("---")
                st.markdown("**Bank Information (Direct Deposit):**")
                st.write(f"🏦 {user_record.get('bank_name', 'N/A')}")
                st.write(f"📍 {user_record.get('bank_address', 'N/A')}")
                st.write(f"💳 Account: •••••{user_record.get('bank_account_number', '')[-4:] if user_record.get('bank_account_number') else 'N/A'}")
                st.write(f"🔢 Routing: {user_record.get('bank_routing_number', 'N/A')}")

                st.markdown("---")
                st.info(f"🔑 Initial PIN: **{user_record.get('passcode', 'N/A')}**")

            with col2:
                st.markdown("### Review & Edit")

                with st.form(f"edit_user_{idx}"):
                    # Editable fields
                    edited_name = st.text_input("Full Name", value=user_record['name'])
                    edited_email = st.text_input("Email", value=user_record.get('email', ''))
                    edited_phone = st.text_input("Phone", value=user_record.get('phone', ''))
                    edited_role = st.selectbox("Role", ["AUDITOR", "MANAGER", "ADMIN"],
                                               index=0 if user_record.get('role') == 'AUDITOR' else
                                                     1 if user_record.get('role') == 'MANAGER' else 2)

                    st.markdown("### Actions")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        approve = st.form_submit_button("✅ Approve", type="primary", use_container_width=True)
                    with col_b:
                        reject = st.form_submit_button("❌ Reject", use_container_width=True)

                    if approve:
                        # Update user record with edits and approve
                        update_data = {
                            "name": edited_name,
                            "email": edited_email,
                            "phone": edited_phone,
                            "role": edited_role,
                            "approval_status": "approved",
                            "approved_by": admin_id,
                            "approved_at": datetime.now(timezone.utc).isoformat()
                        }

                        client_db = get_client(service_role=True)
                        result = client_db.table("app_users").update(update_data).eq("id", user_record['id']).execute()

                        if result.data:
                            st.success(f"✅ Approved: {edited_name}")
                            st.info(f"User can now log in with PIN: {user_record.get('passcode')}")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Failed to approve. Please try again.")

                    if reject:
                        # Delete the pending registration
                        client_db = get_client(service_role=True)
                        result = client_db.table("app_users").delete().eq("id", user_record['id']).execute()

                        if result.data:
                            st.warning(f"❌ Rejected: {user_record['name']}")
                            st.rerun()
                        else:
                            st.error("Failed to reject. Please try again.")

st.markdown("---")

# Show recently approved
with st.expander("📊 Recently Approved Users"):
    approved = client.table("app_users").select("id, name, email, role, approved_at").eq("approval_status", "approved").order("approved_at", desc=True).limit(10).execute()
    if approved.data:
        for u in approved.data:
            st.write(f"✅ **{u['name']}** ({u['role']}) - Approved {u.get('approved_at', 'N/A')}")
    else:
        st.info("No approved users yet.")
