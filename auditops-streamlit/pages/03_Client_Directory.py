"""
Client Directory
View all active clients with complete information.
"""
import streamlit as st
from src.pin_auth import require_authentication, require_role, get_current_user
from src.config import ROLE_AUDITOR
from src.db import get_all_clients, get_client_secrets, log_secrets_access
from datetime import datetime, timezone, timedelta

# Page config
st.set_page_config(page_title="Client Directory", page_icon="📂", layout="wide")

# Authentication
require_authentication()
require_role(ROLE_AUDITOR)

# Get current user
user = get_current_user()
auditor_id = user.get('id') if user else None

st.title("📂 Client Directory")
st.markdown("Browse all active clients and access site information.")
st.markdown("---")

# Initialize session state for secrets
if "directory_secrets_visible_until" not in st.session_state:
    st.session_state.directory_secrets_visible_until = {}
if "directory_revealed_secrets" not in st.session_state:
    st.session_state.directory_revealed_secrets = {}

# Get all active clients
clients = get_all_clients(active_only=True)

if not clients:
    st.warning("No active clients found.")
    st.info("Contact an administrator to add clients to the system.")
else:
    st.metric("Active Clients", len(clients))
    st.markdown("---")

    # Search bar
    search = st.text_input("🔍 Search clients", placeholder="Search by name, address, or contact...")

    # Filter clients based on search
    if search:
        search_lower = search.lower()
        filtered_clients = [
            c for c in clients
            if search_lower in c.get('name', '').lower()
            or search_lower in c.get('address', '').lower()
            or search_lower in c.get('contact_person', '').lower()
        ]
    else:
        filtered_clients = clients

    st.caption(f"Showing {len(filtered_clients)} of {len(clients)} clients")
    st.markdown("---")

    # Display clients in expandable cards
    for client in filtered_clients:
        client_id = client['id']
        now_utc = datetime.now(timezone.utc)

        # Check if secrets are visible for this client
        secrets_visible_until = st.session_state.directory_secrets_visible_until.get(client_id)
        secrets_visible = (
            secrets_visible_until is not None
            and now_utc < secrets_visible_until
        )

        # Clear expired secrets
        if secrets_visible_until and now_utc >= secrets_visible_until:
            st.session_state.directory_secrets_visible_until[client_id] = None
            st.session_state.directory_revealed_secrets[client_id] = None

        with st.expander(f"📍 {client['name']}", expanded=False):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"### {client['name']}")
                st.markdown(f"**Address:** {client.get('address', 'N/A')}")

                st.markdown("---")
                st.markdown("**Contact Information:**")
                if client.get('contact_person'):
                    st.write(f"👤 {client.get('contact_person')}")
                if client.get('contact_email'):
                    st.write(f"📧 {client.get('contact_email')}")
                if client.get('contact_phone'):
                    st.write(f"📞 {client.get('contact_phone')}")

                # WiFi info if available
                if client.get('wifi_name'):
                    st.markdown("---")
                    st.markdown("**WiFi Information:**")
                    st.write(f"📶 Network: {client.get('wifi_name')}")
                    if client.get('wifi_password'):
                        st.write(f"🔑 Password: {client.get('wifi_password')}")

                # Site Access Codes
                has_codes = any([
                    client.get('alarm_code'),
                    client.get('lockbox_code'),
                    client.get('code_for_lights'),
                    client.get('cage_lock_code'),
                    client.get('patio_code')
                ])
                if has_codes:
                    st.markdown("---")
                    st.markdown("**Site Access Codes:**")
                    if client.get('alarm_code'):
                        st.write(f"🚨 Alarm Code: {client.get('alarm_code')}")
                    if client.get('lockbox_code'):
                        st.write(f"🔒 Lock Box Code: {client.get('lockbox_code')}")
                    if client.get('code_for_lights'):
                        st.write(f"💡 Code for Lights: {client.get('code_for_lights')}")
                    if client.get('cage_lock_code'):
                        st.write(f"🔐 CAGE LOCK/PAD LOCK: {client.get('cage_lock_code')}")
                    if client.get('patio_code'):
                        st.write(f"🏡 PATIO CODE: {client.get('patio_code')}")

                # Audit Schedule
                if client.get('audit_day'):
                    st.markdown("---")
                    st.markdown("**Audit Schedule:**")
                    st.write(f"📅 Audit Day: {client.get('audit_day')}")

                # Special instructions
                if client.get('special_instructions'):
                    st.markdown("---")
                    st.markdown("**Special Instructions:**")
                    st.info(client.get('special_instructions'))

                # Notes
                if client.get('notes'):
                    st.markdown("---")
                    st.markdown(f"**Notes:** {client.get('notes')}")

            with col2:
                st.markdown("### 🔐 Site Codes")
                st.caption("Alarm codes, lockbox codes, and other secure information")

                # Reveal secrets button
                if st.button("🔓 Reveal Codes (60s)", key=f"reveal_{client_id}"):
                    secrets = get_client_secrets(client_id)
                    if secrets is None:
                        st.warning("No secure codes available for this client.")
                        st.session_state.directory_revealed_secrets[client_id] = None
                    else:
                        st.session_state.directory_revealed_secrets[client_id] = secrets
                        st.session_state.directory_secrets_visible_until[client_id] = now_utc + timedelta(seconds=60)
                        fields_accessed = list(secrets.keys())
                        log_secrets_access(client_id, auditor_id, fields_accessed, "Client Directory view")
                        st.rerun()

                # Display secrets if visible
                if secrets_visible:
                    secrets = st.session_state.directory_revealed_secrets.get(client_id)
                    if secrets:
                        remaining = (st.session_state.directory_secrets_visible_until[client_id] - now_utc).total_seconds()
                        st.info(f"⏱️ Visible for {int(remaining)} more seconds")

                        if secrets.get("alarm_code"):
                            st.markdown(f"**🚨 Alarm Code:** {secrets.get('alarm_code')}")
                        if secrets.get("lockbox_code"):
                            st.markdown(f"**🔒 Lockbox Code:** {secrets.get('lockbox_code')}")
                        if secrets.get("wifi_name"):
                            st.markdown(f"**📶 WiFi:** {secrets.get('wifi_name')}")
                        if secrets.get("wifi_password"):
                            st.markdown(f"**🔑 WiFi Password:** {secrets.get('wifi_password')}")
                        if secrets.get("other_site_notes"):
                            st.markdown("**📝 Other Notes:**")
                            st.text(secrets.get('other_site_notes'))
                else:
                    st.caption("Click button above to reveal codes")

            st.markdown("---")
