"""
Admin Pay Periods - Select and manage auto-generated pay periods.
"""
import streamlit as st
from datetime import date, timedelta, datetime
from src.pin_auth import require_authentication, require_role
from src.config import ROLE_ADMIN, PAY_PERIOD_OPEN, PAY_PERIOD_LOCKED
from src.db import (
    get_all_pay_periods, lock_pay_period, get_pay_items_by_period
)
from src.utils import format_date, format_currency, format_duration
from src.pdf_statements import generate_pay_period_summary_pdf
import pandas as pd

# Page config
st.set_page_config(page_title="Pay Periods", layout="wide")

# Authentication and role check
require_authentication()
require_role(ROLE_ADMIN)

st.title("📅 Pay Periods")
st.markdown("Select and manage pay periods.")
st.info("💡 **Recurring Schedule**: Pay periods run Saturday to Friday (14 days), with pay date the following Friday. First period: Dec 27, 2025 - Jan 9, 2026 → Pay: Jan 16, 2026")

# Load all pay periods
pay_periods = get_all_pay_periods(use_service_role=True)

if not pay_periods:
    # No pay periods exist - show setup instructions
    st.warning("⚠️ **No pay periods found in database**")

    st.markdown("### 🚀 First Time Setup")
    st.markdown("Pay periods are auto-generated via SQL. Follow these steps:")

    with st.expander("📋 Setup Instructions", expanded=True):
        st.markdown("""
        1. Go to **Supabase** → **SQL Editor**
        2. Open the file: `sql_diagnostics/setup_recurring_pay_periods.sql`
        3. Copy the entire contents
        4. Paste into SQL Editor and click **Run**

        This will:
        - ✅ Add `pay_date` column to pay_periods table
        - ✅ Create SQL functions for generating periods
        - ✅ Populate ~130 pay periods (~5 years worth)
        - ✅ Validate the schedule

        **After running the script**, refresh this page to see all pay periods.
        """)

        st.code("""
-- Quick verification query (run in Supabase SQL Editor)
SELECT COUNT(*) AS total_periods,
       MIN(start_date) AS first_period,
       MAX(end_date) AS last_period
FROM pay_periods;
        """, language="sql")

    st.info("📖 For detailed documentation, see: `sql_diagnostics/README_PAY_PERIODS.md`")
    st.stop()

# Pay periods exist - show selection interface
st.success(f"✅ **{len(pay_periods)} pay periods loaded**")

# Validate data structure - check if any periods are missing 'id' field
missing_id_count = sum(1 for p in pay_periods if not p.get("id"))
if missing_id_count > 0:
    st.error(f"⚠️ **Database Structure Issue**: {missing_id_count} pay period(s) are missing the 'id' field!")
    with st.expander("🔧 How to Fix This", expanded=True):
        st.markdown("""
        Your pay_periods table is missing the `id` column. This is required for proper functionality.

        **To fix this:**
        1. Go to **Supabase** → **SQL Editor**
        2. Run the fix script: `sql_diagnostics/fix_missing_id_column.sql`
        3. This will add the `id` column and migrate your existing data
        4. Refresh this page

        **Note**: The app will still work in read-only mode for viewing periods, but you cannot lock periods or view pay items until this is fixed.
        """)
    st.markdown("---")

# Summary stats
open_count = sum(1 for p in pay_periods if p.get("status") == PAY_PERIOD_OPEN)
locked_count = sum(1 for p in pay_periods if p.get("status") == PAY_PERIOD_LOCKED)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Periods", len(pay_periods))
with col2:
    st.metric("Open Periods", open_count)
with col3:
    st.metric("Locked Periods", locked_count)

st.markdown("---")

# Find current pay period (based on today's date)
today = date.today()
current_period = None
for period in pay_periods:
    start_str = period.get("start_date")
    end_str = period.get("end_date")

    # Parse dates safely
    try:
        if isinstance(start_str, str):
            start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00")).date()
        else:
            start_date = start_str

        if isinstance(end_str, str):
            end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00")).date()
        else:
            end_date = end_str

        if start_date <= today <= end_date:
            current_period = period
            break
    except Exception:
        continue

# Filter options
st.subheader("📋 Select Pay Period")

filter_col1, filter_col2 = st.columns([2, 1])

with filter_col1:
    filter_option = st.radio(
        "Show:",
        ["Current Period", "All Periods", "Open Periods Only", "Locked Periods Only"],
        horizontal=True,
        label_visibility="collapsed"
    )

with filter_col2:
    # Search by date range
    search_enabled = st.checkbox("🔍 Search by date")

# Apply filters
filtered_periods = pay_periods.copy()

if filter_option == "Current Period" and current_period:
    filtered_periods = [current_period]
elif filter_option == "Open Periods Only":
    filtered_periods = [p for p in pay_periods if p.get("status") == PAY_PERIOD_OPEN]
elif filter_option == "Locked Periods Only":
    filtered_periods = [p for p in pay_periods if p.get("status") == PAY_PERIOD_LOCKED]

# Search by date
if search_enabled:
    search_col1, search_col2 = st.columns(2)
    with search_col1:
        search_start = st.date_input("From date:", value=today - timedelta(days=30))
    with search_col2:
        search_end = st.date_input("To date:", value=today + timedelta(days=30))

    # Filter by date range
    temp_filtered = []
    for period in filtered_periods:
        try:
            start_str = period.get("start_date")
            if isinstance(start_str, str):
                period_start = datetime.fromisoformat(start_str.replace("Z", "+00:00")).date()
            else:
                period_start = start_str

            if search_start <= period_start <= search_end:
                temp_filtered.append(period)
        except Exception:
            continue
    filtered_periods = temp_filtered

if not filtered_periods:
    st.warning("No pay periods match your filter criteria.")
    st.stop()

# Show filtered periods count
if len(filtered_periods) < len(pay_periods):
    st.caption(f"Showing {len(filtered_periods)} of {len(pay_periods)} periods")

# Create dropdown options
period_options = {}
for p in filtered_periods:
    # Use id if available, otherwise create unique key from dates
    period_key = p.get("id")
    if not period_key:
        # Fallback: use combination of start_date and end_date as unique identifier
        period_key = f"{p.get('start_date')}_{p.get('end_date')}"

    period_label = f"{format_date(p.get('start_date'))} - {format_date(p.get('end_date'))}"

    # Check if this is the current period
    is_current = False
    if current_period:
        if current_period.get("id") and p.get("id"):
            is_current = p.get("id") == current_period.get("id")
        else:
            # Fallback comparison using dates
            is_current = (p.get("start_date") == current_period.get("start_date") and
                         p.get("end_date") == current_period.get("end_date"))

    if is_current:
        period_label = f"⭐ CURRENT: {period_label}"
    elif p.get("status") == PAY_PERIOD_LOCKED:
        period_label = f"🔒 {period_label}"
    else:
        period_label = f"📅 {period_label}"

    period_options[period_key] = period_label

# Default to current period if available
default_index = 0
if current_period:
    current_key = current_period.get("id")
    if not current_key:
        current_key = f"{current_period.get('start_date')}_{current_period.get('end_date')}"
    if current_key in period_options:
        default_index = list(period_options.keys()).index(current_key)

selected_period_id = st.selectbox(
    "Select pay period to view details:",
    list(period_options.keys()),
    index=default_index,
    format_func=lambda x: period_options[x]
)

st.markdown("---")

# Show selected period details
if selected_period_id:
    # Find selected period - handle both id-based and date-based keys
    selected_period = None
    if "_" in str(selected_period_id):
        # Date-based key: "start_date_end_date"
        parts = str(selected_period_id).split("_", 1)
        if len(parts) == 2:
            search_start, search_end = parts[0], parts[1]
            selected_period = next((p for p in pay_periods
                                   if str(p.get("start_date")) == search_start and str(p.get("end_date")) == search_end), None)
    else:
        # ID-based key
        selected_period = next((p for p in pay_periods if p.get("id") == selected_period_id), None)

    if selected_period:
        # Period info
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Period Information")
            st.markdown(f"**Period:** {format_date(selected_period.get('start_date'))} to {format_date(selected_period.get('end_date'))}")
            st.markdown(f"**Pay Date:** {format_date(selected_period.get('pay_date', 'N/A'))}")
            st.markdown(f"**Status:** {selected_period.get('status', 'open').upper()}")

            # Show if this is the current period
            is_current_period = False
            if current_period:
                if current_period.get("id") and selected_period.get("id"):
                    is_current_period = selected_period.get("id") == current_period.get("id")
                else:
                    # Fallback comparison using dates
                    is_current_period = (selected_period.get("start_date") == current_period.get("start_date") and
                                       selected_period.get("end_date") == current_period.get("end_date"))
            if is_current_period:
                st.success("⭐ This is the current pay period")

        with col2:
            st.subheader("Actions")
            if selected_period.get("status") == PAY_PERIOD_OPEN:
                # Get the actual UUID id for database operations
                period_db_id = selected_period.get("id")
                if not period_db_id:
                    st.error("⚠️ Cannot lock period: Missing ID field. Please run the SQL fix script.")
                    st.caption("See: sql_diagnostics/fix_missing_id_column.sql")
                elif st.button("🔒 Lock Period", type="primary", use_container_width=True, key=f"lock_{selected_period_id}"):
                    result = lock_pay_period(period_db_id, use_service_role=True)
                    if result:
                        st.success("✅ Pay period locked successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to lock period.")
                if period_db_id:
                    st.caption("Lock this period to prevent changes to pay items")
            else:
                st.info("🔒 Period is locked")
                st.caption("Locked periods cannot be modified")

        st.markdown("---")

        # Pay items for this period
        st.subheader("💰 Pay Items")
        # Get the actual UUID id for database operations
        period_db_id = selected_period.get("id")
        if period_db_id:
            pay_items = get_pay_items_by_period(period_db_id, use_service_role=True)
        else:
            pay_items = []
            st.warning("⚠️ Cannot load pay items: Missing ID field. Please run the SQL fix script.")
            st.caption("See: sql_diagnostics/fix_missing_id_column.sql")

        if pay_items:
            # Summary
            total_hours = sum(float(item.get("hours", 0)) for item in pay_items)
            total_amount = sum(float(item.get("amount", 0)) for item in pay_items)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Hours", format_duration(total_hours))
            with col2:
                st.metric("Total Amount", format_currency(total_amount))
            with col3:
                st.metric("Employees", len(pay_items))

            # Items table
            items_data = []
            for item in pay_items:
                auditor = item.get("auditor") or {}
                items_data.append({
                    "Auditor": auditor.get("full_name", "Unknown"),
                    "Hours": f"{float(item.get('hours', 0)):.2f}",
                    "Rate": format_currency(item.get("rate")),
                    "Amount": format_currency(item.get("amount"))
                })

            items_df = pd.DataFrame(items_data)
            st.dataframe(items_df, use_container_width=True, hide_index=True)

            # Download summary PDF
            st.markdown("---")
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("📄 Generate Summary PDF", type="primary", use_container_width=True):
                    with st.spinner("Generating PDF..."):
                        pdf_buffer = generate_pay_period_summary_pdf(
                            pay_period=selected_period,
                            all_pay_items=pay_items
                        )

                        period_label = f"{format_date(selected_period.get('start_date'))}_{format_date(selected_period.get('end_date'))}"
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_buffer.getvalue(),
                            file_name=f"pay_period_summary_{period_label}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
            with col2:
                st.caption("Generate a PDF summary of all pay items for this period")
        else:
            st.info("📭 No pay items for this period yet.")
            st.caption("Pay items will appear here once shifts are approved and processed.")
