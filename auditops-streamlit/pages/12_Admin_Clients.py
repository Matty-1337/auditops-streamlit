"""
Admin Clients - Manage client profiles.
"""
import streamlit as st
from src.pin_auth import require_authentication, require_role
from src.config import ROLE_ADMIN
from src.db import get_all_clients, create_client, update_client, delete_client, get_client_by_id
from src.utils import format_date

# Page config
st.set_page_config(page_title="Clients", layout="wide")

# Authentication and role check
require_authentication()
require_role(ROLE_ADMIN)

st.title("🏢 Clients")
st.markdown("Manage client profiles.")

# Create new client
with st.expander("➕ Create New Client", expanded=False):
    with st.form("create_client_form"):
        name = st.text_input("Client Name *", placeholder="Acme Corporation")
        address = st.text_area("Address", placeholder="123 Main St, City, State ZIP")
        notes = st.text_area("Notes", placeholder="Additional information about this client...")
        is_active = st.checkbox("Active", value=True)
        
        if st.form_submit_button("Create Client", type="primary"):
            if not name:
                st.error("Client name is required.")
            else:
                data = {
                    "name": name,
                    "address": address if address else None,
                    "notes": notes if notes else None,
                    "is_active": is_active
                }
                result = create_client(data, use_service_role=True)
                if result:
                    st.success(f"Client '{name}' created successfully!")
                    st.rerun()
                else:
                    st.error("Failed to create client.")

# List clients
st.subheader("All Clients")
clients = get_all_clients(active_only=False)

if clients:
    # Filter options
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search clients", placeholder="Search by name...")
    with col2:
        show_inactive = st.checkbox("Show inactive", value=False)
    
    # Filter clients
    filtered_clients = clients
    if search:
        filtered_clients = [c for c in filtered_clients if search.lower() in c.get("name", "").lower()]
    if not show_inactive:
        filtered_clients = [c for c in filtered_clients if c.get("is_active", True)]
    
    # Display clients
    for client in filtered_clients:
        with st.expander(f"{client.get('name')} {'✅' if client.get('is_active') else '❌'}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**ID:** `{client.get('id')}`")
                if client.get("address"):
                    st.markdown(f"**Address:** {client.get('address')}")
                if client.get("notes"):
                    st.markdown(f"**Notes:** {client.get('notes')}")
                st.markdown(f"**Created:** {format_date(client.get('created_at'))}")
            
            with col2:
                status_text = "Active" if client.get("is_active") else "Inactive"
                st.markdown(f"**Status:** {status_text}")
                
                # Edit form
                with st.form(f"edit_client_{client['id']}"):
                    new_name = st.text_input("Name", value=client.get("name"), key=f"name_{client['id']}")
                    new_address = st.text_area("Address", value=client.get("address") or "", key=f"address_{client['id']}")
                    new_notes = st.text_area("Notes", value=client.get("notes") or "", key=f"notes_{client['id']}")
                    new_active = st.checkbox("Active", value=client.get("is_active", True), key=f"active_{client['id']}")
                    
                    col_save, col_delete = st.columns(2)
                    with col_save:
                        if st.form_submit_button("💾 Save", use_container_width=True):
                            update_data = {
                                "name": new_name,
                                "address": new_address if new_address else None,
                                "notes": new_notes if new_notes else None,
                                "is_active": new_active
                            }
                            result = update_client(client["id"], update_data, use_service_role=True)
                            if result:
                                st.success("Client updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update client.")
                    
                    with col_delete:
                        if st.form_submit_button("🗑️ Delete", use_container_width=True):
                            result = delete_client(client["id"], use_service_role=True)
                            if result:
                                st.success("Client deactivated.")
                                st.rerun()
                            else:
                                st.error("Failed to deactivate client.")
else:
    st.info("No clients found. Create one to get started.")

