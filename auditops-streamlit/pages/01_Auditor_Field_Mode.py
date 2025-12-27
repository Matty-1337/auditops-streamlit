"""
Auditor Field Mode - Check in/out and manage shifts.
"""
import streamlit as st
from datetime import datetime, timezone
from src.pin_auth import require_authentication, require_role, get_current_user
from src.config import ROLE_AUDITOR, SHIFT_STATUS_DRAFT, SHIFT_STATUS_SUBMITTED
from src.db import (
    get_shifts_by_auditor, create_shift, update_shift, submit_shift,
    get_all_clients
)
from src.utils import format_datetime, format_duration, calculate_hours, get_client_display_name

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

# Process shifts to find open_shift and submit_ready_shift
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

# Main content area
st.subheader("Current Shift")

if open_shift:
    st.success("✅ You have an active shift")
    st.markdown(f"**Client:** {get_client_display_name(open_shift.get('client'))}")
    st.markdown(f"**Check-in:** {format_datetime(open_shift.get('check_in'))}")
    st.markdown(f"**Status:** {open_shift.get('status', 'draft').upper()}")

    if open_shift.get("notes"):
        st.markdown(f"**Notes:** {open_shift.get('notes')}")

    # Client Profile Section
    st.markdown("---")

    # Get full client details
    client_id = open_shift.get("client_id")
    if client_id:
        all_clients = get_all_clients(active_only=False)
        client_detail = next((c for c in all_clients if c["id"] == client_id), None)

        if client_detail:
            with st.expander(f"📋 **{client_detail.get('name', 'Client')} - Full Profile**", expanded=True):
                st.markdown(f"## {client_detail.get('name', 'Client Profile')}")

                # Location Section
                st.markdown("### Location:")
                if client_detail.get('address'):
                    st.markdown(f"📍 {client_detail.get('address')}")
                else:
                    st.markdown("📍 None")

                # WiFi Information Section
                st.markdown("---")
                st.markdown("### WiFi Information:")
                if client_detail.get('wifi_name'):
                    st.markdown(f"📶 **Network:** {client_detail.get('wifi_name')}")
                    if client_detail.get('wifi_password'):
                        st.markdown(f"🔑 **Password:** {client_detail.get('wifi_password')}")
                    else:
                        st.markdown("🔑 **Password:** None")
                else:
                    st.markdown("📶 None")

                # Site Access Codes Section
                st.markdown("---")
                st.markdown("### Site Access Codes:")
                col1, col2 = st.columns(2)

                with col1:
                    if client_detail.get('alarm_code'):
                        st.markdown(f"🚨 **Alarm Code:** {client_detail.get('alarm_code')}")
                    else:
                        st.markdown("🚨 **Alarm Code:** None")

                    if client_detail.get('code_for_lights'):
                        st.markdown(f"💡 **Code for Lights:** {client_detail.get('code_for_lights')}")
                    else:
                        st.markdown("💡 **Code for Lights:** None")

                with col2:
                    if client_detail.get('lockbox_code'):
                        st.markdown(f"🔒 **Lock Box Code:** {client_detail.get('lockbox_code')}")
                    else:
                        st.markdown("🔒 **Lock Box Code:** None")

                    if client_detail.get('cage_lock_code'):
                        st.markdown(f"🔐 **CAGE LOCK/PAD LOCK:** {client_detail.get('cage_lock_code')}")
                    else:
                        st.markdown("🔐 **CAGE LOCK/PAD LOCK:** None")

    st.markdown("---")

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

                    if client_detail.get('wifi_name'):
                        st.markdown(f"**WiFi:** {client_detail.get('wifi_name')}")
                        if client_detail.get('wifi_password'):
                            st.markdown(f"**WiFi Password:** {client_detail.get('wifi_password')}")

                    if client_detail.get('special_instructions'):
                        st.info(f"**Special Instructions:** {client_detail.get('special_instructions')}")

                    # Show hint about site codes
                    st.caption("💡 Site access codes (alarm, lockbox, etc.) available after check-in")
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
