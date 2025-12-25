"""
Admin Health Check - System health and connectivity checks.
"""
import streamlit as st
from datetime import datetime
from src.auth import require_authentication
from src.config import require_role_access, ROLE_ADMIN, validate_config, get_supabase_url, get_supabase_key
from src.supabase_client import get_client, reset_clients
from src.db import get_all_clients, get_all_profiles

# Page config
st.set_page_config(page_title="Health Check", layout="wide")

# Authentication and role check
require_authentication()
require_role_access(ROLE_ADMIN)

st.title("🏥 Health Check")
st.markdown("System connectivity and configuration status.")

# Status indicators
def check_status(name: str, status: bool, message: str = ""):
    """Display a status check result."""
    icon = "✅" if status else "❌"
    color = "green" if status else "red"
    st.markdown(f"{icon} **{name}**")
    if message:
        st.caption(f"  {message}")
    return status

results = {}

# Configuration check
st.subheader("Configuration")
try:
    validate_config()
    results["config"] = check_status("Configuration", True, "All required secrets are present")
except Exception as e:
    results["config"] = check_status("Configuration", False, str(e))

# Supabase URL
url = get_supabase_url()
results["url"] = check_status("Supabase URL", bool(url), url if url else "Missing")

# Supabase Keys
anon_key = get_supabase_key(service_role=False)
service_key = get_supabase_key(service_role=True)
results["anon_key"] = check_status("Anon Key", bool(anon_key), "Present" if anon_key else "Missing")
results["service_key"] = check_status("Service Role Key", bool(service_key), "Present" if service_key else "Missing")

# Database connectivity
st.subheader("Database Connectivity")
try:
    client = get_client(service_role=False)
    # Test query - schema-agnostic (doesn't assume id column)
    test_result = client.table("profiles").select("*").limit(1).execute()
    results["db_anon"] = check_status("Database (Anon Key)", True, "Connected successfully")
except Exception as e:
    results["db_anon"] = check_status("Database (Anon Key)", False, str(e))

try:
    client_service = get_client(service_role=True)
    # Test query - schema-agnostic (doesn't assume id column)
    test_result = client_service.table("profiles").select("*").limit(1).execute()
    results["db_service"] = check_status("Database (Service Key)", True, "Connected successfully")
except Exception as e:
    results["db_service"] = check_status("Database (Service Key)", False, str(e))

# Table checks
st.subheader("Table Access")
tables = ["profiles", "clients", "shifts", "pay_periods", "pay_items", "approvals", "access_logs"]

for table in tables:
    try:
        client = get_client(service_role=True)
        # Schema-agnostic check - doesn't assume id column exists
        result = client.table(table).select("*").limit(1).execute()
        check_status(f"Table: {table}", True, "Accessible")
        results[f"table_{table}"] = True
    except Exception as e:
        check_status(f"Table: {table}", False, str(e))
        results[f"table_{table}"] = False

# Data counts
st.subheader("Data Counts")
try:
    clients = get_all_clients(active_only=False)
    profiles = get_all_profiles(active_only=False, use_service_role=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Clients", len(clients))
        st.metric("Active Clients", sum(1 for c in clients if c.get("is_active")))
    with col2:
        st.metric("Total Profiles", len(profiles))
        st.metric("Active Profiles", sum(1 for p in profiles if p.get("is_active")))
    
    results["data_counts"] = True
except Exception as e:
    st.error(f"Failed to get data counts: {str(e)}")
    results["data_counts"] = False

# Storage check (if bucket exists)
st.subheader("Storage")
try:
    client = get_client(service_role=True)
    # Try to list buckets (this will fail if storage not configured)
    buckets = client.storage.list_buckets()
    if buckets:
        check_status("Storage", True, f"{len(buckets)} bucket(s) available")
        results["storage"] = True
    else:
        check_status("Storage", False, "No buckets configured")
        results["storage"] = False
except Exception as e:
    check_status("Storage", False, f"Storage not accessible: {str(e)}")
    results["storage"] = False

# Overall status
st.subheader("Overall Status")
all_passed = all(results.values())
if all_passed:
    st.success("✅ All health checks passed!")
else:
    st.warning("⚠️ Some health checks failed. Review the details above.")

# Refresh button
if st.button("🔄 Refresh Health Check", type="primary"):
    reset_clients()
    st.rerun()

# Timestamp
st.caption(f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

