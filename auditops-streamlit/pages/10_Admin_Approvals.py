"""
Admin/Manager Approvals - Review and approve submitted shifts.
"""
import streamlit as st
import logging
from src.pin_auth import require_authentication, require_role, get_current_user
from src.config import ROLE_MANAGER, ROLE_ADMIN, SHIFT_STATUS_SUBMITTED, SHIFT_STATUS_APPROVED, SHIFT_STATUS_REJECTED
from src.db import get_submitted_shifts, get_shift, create_approval, get_approvals_by_shift
from src.utils import format_datetime, format_duration, calculate_hours, get_client_display_name, get_user_display_name

# Try to import diagnostic function (optional, for troubleshooting)
try:
    from src.db import diagnose_approvals_query
    DIAGNOSTICS_AVAILABLE = True
except ImportError as e:
    DIAGNOSTICS_AVAILABLE = False
    logging.warning(f"Diagnostic function not available: {e}")

# Page config
st.set_page_config(page_title="Approvals", layout="wide")

# Authentication and role check
require_authentication()
require_role([ROLE_MANAGER, ROLE_ADMIN])

# Get current user
user = get_current_user()
approver_id = user.get('id') if user else None

if not approver_id:
    st.error("User not found.")
    st.stop()

st.title("✅ Approvals")
st.markdown("Review and approve submitted shifts.")

# Get submitted shifts
submitted_shifts = get_submitted_shifts()

if not submitted_shifts:
    st.info("No shifts pending approval.")
else:
    st.metric("Pending Approvals", len(submitted_shifts))
    
    # Display shifts
    for shift in submitted_shifts:
        with st.expander(f"Shift: {get_client_display_name(shift.get('client'))} - {get_user_display_name(shift.get('auditor'))}", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Auditor:** {get_user_display_name(shift.get('auditor'))}")
                st.markdown(f"**Client:** {get_client_display_name(shift.get('client'))}")
                st.markdown(f"**Check-in:** {format_datetime(shift.get('check_in'))}")
                st.markdown(f"**Check-out:** {format_datetime(shift.get('check_out')) or 'Not checked out'}")
                
                # Calculate hours
                hours = calculate_hours(shift.get("check_in"), shift.get("check_out"))
                if hours:
                    st.markdown(f"**Hours:** {format_duration(hours)}")
                
                if shift.get("notes"):
                    st.markdown(f"**Notes:** {shift.get('notes')}")
            
            with col2:
                st.markdown("**Status:** 🟡 SUBMITTED")
                
                # Approval actions using forms
                with st.form(f"approve_form_{shift['id']}"):
                    notes_approve = st.text_input("Approval notes (optional)", key=f"notes_approve_{shift['id']}", placeholder="Optional notes...")
                    if st.form_submit_button("✅ Approve", use_container_width=True, type="primary"):
                        result = create_approval(
                            shift_id=shift["id"],
                            approver_id=approver_id,
                            decision="approved",
                            notes=notes_approve if notes_approve else None
                        )
                        if result:
                            st.success("Shift approved!")
                            st.rerun()
                        else:
                            st.error("Failed to approve shift.")
                
                with st.form(f"reject_form_{shift['id']}"):
                    notes_reject = st.text_input("Rejection notes", key=f"notes_reject_{shift['id']}", placeholder="Required: reason for rejection...")
                    if st.form_submit_button("❌ Reject", use_container_width=True):
                        if not notes_reject:
                            st.error("Please provide a reason for rejection.")
                        else:
                            result = create_approval(
                                shift_id=shift["id"],
                                approver_id=approver_id,
                                decision="rejected",
                                notes=notes_reject
                            )
                            if result:
                                st.success("Shift rejected.")
                                st.rerun()
                            else:
                                st.error("Failed to reject shift.")
            
            # Show previous approvals (with error handling)
            try:
                approvals = get_approvals_by_shift(shift["id"])
                if approvals:
                    st.markdown("**Previous Decisions:**")
                    for approval in approvals:
                        decision = approval.get("decision", "").upper()
                        approver = get_user_display_name(approval.get("approver"))
                        # Use created_at if decided_at doesn't exist
                        decided_at = format_datetime(approval.get("decided_at") or approval.get("created_at"))
                        notes = approval.get("decision_notes", "")
                        st.caption(f"{decision} by {approver} on {decided_at}")
                        if notes:
                            st.caption(f"  Notes: {notes}")
                else:
                    st.caption("_No previous decisions_")
            except Exception as e:
                # Log error but don't crash the approval workflow
                logging.exception(f"Failed to load approval history for shift {shift['id']}")
                st.warning("⚠️ Could not load approval history. You can still approve/reject this shift.")

                # Add diagnostic button for troubleshooting (only show if diagnostics available)
                if DIAGNOSTICS_AVAILABLE:
                    if st.button(f"🔍 Run Diagnostics", key=f"diagnose_{shift['id']}"):
                        with st.expander("Diagnostic Results", expanded=True):
                            try:
                                results = diagnose_approvals_query(shift["id"])
                                st.json(results)
                                st.info("📋 Check the logs at /tmp/postgrest_errors.log for detailed error information")
                            except Exception as diag_err:
                                st.error(f"Diagnostic failed: {str(diag_err)}")

            st.divider()

