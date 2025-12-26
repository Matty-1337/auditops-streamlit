"""
Admin Secrets Access Log - View access logs for protected documents.
"""
import streamlit as st
from src.pin_auth import require_authentication, require_role
from src.config import ROLE_ADMIN
from src.db import get_access_logs, get_all_clients
from src.utils import format_datetime, get_user_display_name, get_client_display_name
import pandas as pd

# Page config
st.set_page_config(page_title="Access Log", layout="wide")

# Authentication and role check
require_authentication()
require_role(ROLE_ADMIN)

st.title("🔒 Secrets Access Log")
st.markdown("Monitor access to protected client documents and sensitive data.")

# Filters
col1, col2, col3 = st.columns(3)
with col1:
    clients = get_all_clients(active_only=False)
    client_options = {None: "All Clients"}
    client_options.update({c["id"]: c["name"] for c in clients})
    selected_client_id = st.selectbox("Filter by Client", list(client_options.keys()), format_func=lambda x: client_options[x])

with col2:
    action_filter = st.selectbox("Filter by Action", ["All", "view", "download", "upload"])

with col3:
    limit = st.number_input("Limit Results", min_value=10, max_value=1000, value=100, step=10)

# Get access logs
client_id_filter = selected_client_id if selected_client_id else None
action_filter_value = action_filter.lower() if action_filter != "All" else None

logs = get_access_logs(
    client_id=client_id_filter,
    user_id=None,
    limit=limit,
    use_service_role=True
)

# Filter by action if needed
if action_filter_value:
    logs = [log for log in logs if log.get("action") == action_filter_value]

# Display logs
if logs:
    st.metric("Total Log Entries", len(logs))
    
    # Prepare table data
    table_data = []
    for log in logs:
        table_data.append({
            "Timestamp": format_datetime(log.get("created_at")),
            "User": get_user_display_name(log.get("user")),
            "Client": get_client_display_name(log.get("client")),
            "Object Path": log.get("object_path", "—"),
            "Action": log.get("action", "—").upper(),
            "IP": log.get("ip_optional", "—")
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Summary stats
    st.subheader("Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    view_count = sum(1 for log in logs if log.get("action") == "view")
    download_count = sum(1 for log in logs if log.get("action") == "download")
    upload_count = sum(1 for log in logs if log.get("action") == "upload")
    unique_users = len(set(log.get("user", {}).get("id", "") for log in logs if log.get("user")))
    
    with col1:
        st.metric("Views", view_count)
    with col2:
        st.metric("Downloads", download_count)
    with col3:
        st.metric("Uploads", upload_count)
    with col4:
        st.metric("Unique Users", unique_users)
    
    # Export option
    if st.button("📥 Export to CSV"):
        from datetime import datetime
        csv = df.to_csv(index=False)
        timestamp = datetime.now().strftime('%Y%m%d')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"access_log_{timestamp}.csv",
            mime="text/csv"
        )
else:
    st.info("No access logs found.")

