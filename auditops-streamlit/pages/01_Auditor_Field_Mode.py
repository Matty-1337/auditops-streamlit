"""
Auditor Field Mode - Check in/out and manage shifts.
"""
import streamlit as st
from datetime import datetime, timezone, timedelta
from src.pin_auth import require_authentication, require_role, get_current_user
from src.config import ROLE_AUDITOR, SHIFT_STATUS_DRAFT, SHIFT_STATUS_SUBMITTED
from src.db import (
    get_shifts_by_auditor, create_shift, update_shift, submit_shift,
    get_all_clients, get_client_secrets, log_secrets_access
)
from src.utils import format_datetime, format_duration, calculate_hours, render_status_badge, get_client_display_name

# Page config
st.set_page_config(page_title="Field Mode", layout="wide")

# Authentication and role check
require_authentication()
require_role(ROLE_AUDITOR)

# Get current user
user = get_current_user()
auditor_id = user.get('id') if user else None

if not auditor_id:
    st.error("User not found. Please log out and log back in.")
    st.stop()

st.title("📱 Field Mode")
st.markdown("Check in/out and manage your shifts.")

# Get shifts and identify open_shift and submit_ready_shift
today_utc = datetime.now(timezone.utc).date()

# Add error handling for shift query
try:
    all_shifts = get_shifts_by_auditor(auditor_id, status=None)
except Exception as e:
    st.error(f"⚠️ Error loading shifts: {str(e)}")

    # Show diagnostic information
    with st.expander("🔍 Diagnostic Information"):
        st.write("**User Information:**")
        st.write(f"- User ID: {auditor_id}")
        st.write(f"- Name: {user.get('name') if user else 'N/A'}")
        st.write(f"- Role: {user.get('role') if user else 'N/A'}")

        st.write("\n**Troubleshooting Steps:**")
        st.write("1. Verify your profile has the 'AUDITOR' role in the database")
        st.write("2. Contact an administrator to verify your permissions")

    st.stop()

all_shifts
open_shift = None
submit_ready_shift = None

def safe_parse_iso(value):
    """Safely parse ISO datetime string."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

for shift in all_shifts:
    check_in_str = shift.get("check_in")
    check_in_dt = safe_parse_iso(check_in_str)
    check_in_date = check_in_dt.date() if check_in_dt else None
    
    if check_in_date == today_utc:
        status = shift.get("status")
        check_out = shift.get("check_out")
        
        if status in [SHIFT_STATUS_DRAFT, SHIFT_STATUS_SUBMITTED] and not check_out:
            open_shift = shift
        elif status == SHIFT_STATUS_DRAFT and check_out:
            submit_ready_shift = shift

# Initialize session state for secrets
if "secrets_visible_until" not in st.session_state:
    st.session_state.secrets_visible_until = None
if "revealed_secrets_client_id" not in st.session_state:
    st.session_state.revealed_secrets_client_id = None
if "revealed_secrets_payload" not in st.session_state:
    st.session_state.revealed_secrets_payload = None

# Compute current time and secrets visibility
now_utc = datetime.now(timezone.utc)
secrets_visible = (
    st.session_state.secrets_visible_until is not None
    and now_utc < st.session_state.secrets_visible_until
    and st.session_state.revealed_secrets_client_id is not None
)

# Clear expired secrets
if st.session_state.secrets_visible_until is not None and now_utc >= st.session_state.secrets_visible_until:
    st.session_state.secrets_visible_until = None
    st.session_state.revealed_secrets_client_id = None
    st.session_state.revealed_secrets_payload = None

# Main columns
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Current Shift")
    
    if open_shift:
        st.success("✅ You have an active shift")
        st.markdown(f"**Client:** {get_client_display_name(open_shift.get('client'))}")
        st.markdown(f"**Check-in:** {format_datetime(open_shift.get('check_in'))}")
        st.markdown(f"**Status:** {open_shift.get('status', 'draft').upper()}")

        if open_shift.get("notes"):
            st.markdown(f"**Notes:** {open_shift.get('notes')}")

        # Client Information Section
        st.markdown("---")
        st.markdown("### 📋 Client Information")

        # Get full client details
        client_id = open_shift.get("client_id")
        if client_id:
            all_clients = get_all_clients(active_only=False)
            client_detail = next((c for c in all_clients if c["id"] == client_id), None)

            if client_detail:
                st.markdown(f"**Address:** {client_detail.get('address', 'N/A')}")

                if client_detail.get('contact_person'):
                    st.markdown(f"**Contact:** {client_detail.get('contact_person')}")
                if client_detail.get('contact_phone'):
                    st.markdown(f"**Phone:** {client_detail.get('contact_phone')}")
                if client_detail.get('contact_email'):
                    st.markdown(f"**Email:** {client_detail.get('contact_email')}")

                if client_detail.get('wifi_name'):
                    st.markdown(f"**WiFi:** {client_detail.get('wifi_name')}")
                    if client_detail.get('wifi_password'):
                        st.markdown(f"**WiFi Password:** {client_detail.get('wifi_password')}")

                if client_detail.get('special_instructions'):
                    st.info(f"**Special Instructions:** {client_detail.get('special_instructions')}")

        st.markdown("---")

        # Site Info / Secrets section
        st.subheader("🔐 Site Codes (Alarm, Lockbox)")
        if st.button("Reveal Site Info (60s)"):
            client_id = open_shift.get("client_id")
            if client_id:
                secrets = get_client_secrets(client_id)
                if secrets is None:
                    st.warning("No alarm or lockbox codes configured for this client.")
                    st.info("WiFi and contact information are shown above in Client Information.")
                    st.session_state.revealed_secrets_client_id = None
                    st.session_state.revealed_secrets_payload = None
                else:
                    st.session_state.revealed_secrets_payload = secrets
                    st.session_state.revealed_secrets_client_id = client_id
                    st.session_state.secrets_visible_until = now_utc + timedelta(seconds=60)
                    fields_accessed = list(secrets.keys())
                    log_secrets_access(client_id, auditor_id, fields_accessed, "Field Mode reveal")
                    st.rerun()
        
        # Display secrets if visible and client matches
        if secrets_visible and st.session_state.revealed_secrets_client_id == open_shift.get("client_id"):
            secrets = st.session_state.revealed_secrets_payload
            if secrets:
                remaining = (st.session_state.secrets_visible_until - now_utc).total_seconds()
                st.info(f"⏱️ Secrets visible for {int(remaining)} more seconds")
                if secrets.get("wifi_name"):
                    st.markdown(f"**WiFi Name:** {secrets.get('wifi_name')}")
                if secrets.get("wifi_password"):
                    st.markdown(f"**WiFi Password:** {secrets.get('wifi_password')}")
                if secrets.get("alarm_code"):
                    st.markdown(f"**Alarm Code:** {secrets.get('alarm_code')}")
                if secrets.get("lockbox_code"):
                    st.markdown(f"**Lockbox Code:** {secrets.get('lockbox_code')}")
                if secrets.get("other_site_notes"):
                    st.markdown(f"**Other Site Notes:** {secrets.get('other_site_notes')}")
        
        # Check out button
        if st.button("🛑 Check Out", type="primary", use_container_width=True):
            check_out_time = datetime.now(timezone.utc)
            hours = calculate_hours(open_shift.get("check_in"), check_out_time)
            
            update_data = {
                "check_out": check_out_time.isoformat(),
            }
            
            if hours:
                update_data["notes"] = f"{open_shift.get('notes', '')}\n\nHours: {format_duration(hours)}".strip()
            
            result = update_shift(open_shift["id"], update_data)
            if result:
                st.success("Checked out successfully!")
                st.rerun()
            else:
                st.error("Failed to check out. Please try again.")
    elif submit_ready_shift:
        st.info("📋 Draft shift ready to submit")
        st.markdown(f"**Client:** {get_client_display_name(submit_ready_shift.get('client'))}")
        st.markdown(f"**Check-in:** {format_datetime(submit_ready_shift.get('check_in'))}")
        st.markdown(f"**Check-out:** {format_datetime(submit_ready_shift.get('check_out'))}")
        
        if submit_ready_shift.get("notes"):
            st.markdown(f"**Notes:** {submit_ready_shift.get('notes')}")
        
        if st.button("📤 Submit for Approval", use_container_width=True):
            result = submit_shift(submit_ready_shift["id"])
            if result:
                st.success("Shift submitted for approval!")
                st.rerun()
            else:
                st.error("Failed to submit shift.")
    else:
        st.info("No active shift. Check in to start a new shift.")

        # Check in form
        with st.form("check_in_form"):
            st.subheader("Check In")
            clients = get_all_clients(active_only=True)
            client_options = {c["name"]: c["id"] for c in clients}
            client_names = list(client_options.keys())

            if not client_names:
                st.warning("No active clients available. Contact an administrator.")
                selected_client = None
                notes = ""
                # Always include submit button (disabled when no clients)
                st.form_submit_button("✅ Check In", type="primary", use_container_width=True, disabled=True)
            else:
                selected_client = st.selectbox("Select Client", [""] + client_names)

                # Show client details when selected
                if selected_client:
                    st.markdown("---")
                    st.markdown("### 📋 Client Information")
                    selected_client_id = client_options[selected_client]

                    # Get full client details
                    client_detail = next((c for c in clients if c["id"] == selected_client_id), None)
                    if client_detail:
                        st.markdown(f"**Name:** {client_detail.get('name', 'N/A')}")
                        st.markdown(f"**Address:** {client_detail.get('address', 'N/A')}")

                        if client_detail.get('contact_person'):
                            st.markdown(f"**Contact:** {client_detail.get('contact_person')}")
                        if client_detail.get('contact_phone'):
                            st.markdown(f"**Phone:** {client_detail.get('contact_phone')}")
                        if client_detail.get('contact_email'):
                            st.markdown(f"**Email:** {client_detail.get('contact_email')}")

                        if client_detail.get('wifi_name'):
                            st.markdown(f"**WiFi:** {client_detail.get('wifi_name')}")
                            if client_detail.get('wifi_password'):
                                st.markdown(f"**WiFi Password:** {client_detail.get('wifi_password')}")

                        if client_detail.get('special_instructions'):
                            st.info(f"**Special Instructions:** {client_detail.get('special_instructions')}")

                        if client_detail.get('notes'):
                            st.markdown(f"**Notes:** {client_detail.get('notes')}")

                        # Show hint about secrets
                        st.caption("💡 Additional site codes (alarm, lockbox) available after check-in")
                    st.markdown("---")

                notes = st.text_area("Notes (optional)", placeholder="Add any notes about this shift...")

                if st.form_submit_button("✅ Check In", type="primary", use_container_width=True):
                    if not selected_client:
                        st.error("Please select a client.")
                    else:
                        client_id = client_options[selected_client]
                        check_in_time = datetime.now(timezone.utc)

                        shift_data = {
                            "auditor_id": auditor_id,
                            "client_id": client_id,
                            "check_in": check_in_time.isoformat(),
                            "status": SHIFT_STATUS_DRAFT,
                            "notes": notes if notes else None
                        }

                        result = create_shift(shift_data)
                        if result:
                            st.success("Checked in successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to check in. Please try again.")

with col2:
    st.subheader("Recent Shifts")
    
    # Get recent shifts
    recent_shifts = get_shifts_by_auditor(auditor_id)[:10]
    
    if recent_shifts:
        for shift in recent_shifts:
            with st.container():
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**{get_client_display_name(shift.get('client'))}**")
                    st.caption(f"{format_datetime(shift.get('check_in'))} - {format_datetime(shift.get('check_out')) or 'In progress'}")
                with col_b:
                    render_status_badge(shift.get("status", "draft"))
                
                if shift.get("notes"):
                    st.caption(f"📝 {shift.get('notes')[:100]}...")
                
                st.divider()
    else:
        st.info("No shifts yet. Check in to start tracking your time.")

