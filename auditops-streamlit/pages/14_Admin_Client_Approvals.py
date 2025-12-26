"""
Admin Client Approvals
Review and approve/reject pending client registrations.
"""
import streamlit as st
from src.pin_auth import require_authentication, require_role, get_current_user
from src.config import ROLE_ADMIN
from src.supabase_client import get_client
from datetime import datetime, timezone

# Page config
st.set_page_config(page_title="Client Approvals", layout="wide")

# Authentication
require_authentication()
require_role(ROLE_ADMIN)

user = get_current_user()
admin_id = user.get('id')

st.title("🏢 Client Registration Approvals")
st.markdown("Review and approve pending client registrations.")
st.markdown("---")

# Get pending clients
client = get_client(service_role=True)
response = client.table("clients").select("*").eq("approval_status", "pending").order("created_at").execute()
pending_clients = response.data or []

if not pending_clients:
    st.success("✅ No pending client approvals!")
    st.info("New client registrations will appear here for review.")
else:
    st.metric("Pending Approvals", len(pending_clients))

    for idx, client_record in enumerate(pending_clients):
        with st.expander(f"📋 {client_record['client_name']}", expanded=True):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"### {client_record['client_name']}")
                st.markdown(f"**Address:** {client_record.get('address', 'N/A')}")
                st.markdown("---")
                st.markdown("**Contact Information:**")
                st.write(f"👤 {client_record.get('contact_person', 'N/A')}")
                st.write(f"📧 {client_record.get('contact_email', 'N/A')}")
                st.write(f"📞 {client_record.get('contact_phone', 'N/A')}")

                if client_record.get('wifi_name'):
                    st.markdown("---")
                    st.markdown("**WiFi Information:**")
                    st.write(f"📶 Network: {client_record.get('wifi_name')}")
                    if client_record.get('wifi_password'):
                        st.write(f"🔑 Password: {client_record.get('wifi_password')}")

                if client_record.get('special_instructions'):
                    st.markdown("---")
                    st.markdown("**Special Instructions:**")
                    st.info(client_record.get('special_instructions'))

                st.caption(f"Submitted: {client_record.get('created_at', 'N/A')}")

            with col2:
                st.markdown("### Review & Edit")

                with st.form(f"edit_client_{idx}"):
                    # Editable fields
                    edited_name = st.text_input("Company Name", value=client_record['client_name'])
                    edited_address = st.text_area("Address", value=client_record.get('address', ''))
                    edited_contact = st.text_input("Contact Person", value=client_record.get('contact_person', ''))
                    edited_email = st.text_input("Email", value=client_record.get('contact_email', ''))
                    edited_phone = st.text_input("Phone", value=client_record.get('contact_phone', ''))

                    st.markdown("### Actions")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        approve = st.form_submit_button("✅ Approve", type="primary", use_container_width=True)
                    with col_b:
                        reject = st.form_submit_button("❌ Reject", use_container_width=True)

                    if approve:
                        # Update client record with edits and approve
                        update_data = {
                            "client_name": edited_name,
                            "address": edited_address,
                            "contact_person": edited_contact,
                            "contact_email": edited_email,
                            "contact_phone": edited_phone,
                            "active": True,
                            "approval_status": "approved",
                            "approved_by": admin_id,
                            "approved_at": datetime.now(timezone.utc).isoformat()
                        }

                        client_db = get_client(service_role=True)
                        result = client_db.table("clients").update(update_data).eq("client_id", client_record['client_id']).execute()

                        if result.data:
                            st.success(f"✅ Approved: {edited_name}")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Failed to approve. Please try again.")

                    if reject:
                        # Delete the pending registration
                        client_db = get_client(service_role=True)
                        result = client_db.table("clients").delete().eq("client_id", client_record['client_id']).execute()

                        if result.data:
                            st.warning(f"❌ Rejected: {client_record['client_name']}")
                            st.rerun()
                        else:
                            st.error("Failed to reject. Please try again.")

st.markdown("---")

# Show recently approved
with st.expander("📊 Recently Approved Clients"):
    approved = client.table("clients").select("*").eq("approval_status", "approved").order("approved_at", desc=True).limit(10).execute()
    if approved.data:
        for c in approved.data:
            st.write(f"✅ **{c['client_name']}** - Approved {c.get('approved_at', 'N/A')}")
    else:
        st.info("No approved clients yet.")
