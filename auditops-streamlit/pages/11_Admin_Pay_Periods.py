"""
Admin Pay Periods - Manage pay periods and generate summaries.
"""
import streamlit as st
from datetime import date, timedelta
from src.pin_auth import require_authentication, require_role
from src.config import ROLE_ADMIN, PAY_PERIOD_OPEN, PAY_PERIOD_LOCKED
from src.db import (
    get_all_pay_periods, create_pay_period, lock_pay_period, get_pay_items_by_period,
    get_all_pay_periods as get_periods, get_shifts_by_auditor
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
st.markdown("Create and manage pay periods.")

# Create new pay period
with st.expander("➕ Create New Pay Period", expanded=False):
    with st.form("create_period_form"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today())
        with col2:
            end_date = st.date_input("End Date", value=date.today() + timedelta(days=13))
        
        if st.form_submit_button("Create Pay Period", type="primary"):
            if end_date <= start_date:
                st.error("❌ End date must be after start date.")
            else:
                try:
                    result = create_pay_period(start_date, end_date, use_service_role=True)
                    if result:
                        st.success(f"✅ Pay period created: {format_date(start_date)} to {format_date(end_date)}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to create pay period. A pay period with dates {format_date(start_date)} to {format_date(end_date)} already exists.")
                except Exception as e:
                    st.error(f"❌ Error creating pay period: {str(e)}")
                    st.info("💡 Please check that:\n- The dates don't overlap with existing pay periods\n- You have admin permissions\n- The database connection is working")

# List pay periods
st.subheader("Pay Periods")
pay_periods = get_all_pay_periods(use_service_role=True)

if pay_periods:
    # Summary stats
    open_count = sum(1 for p in pay_periods if p.get("status") == PAY_PERIOD_OPEN)
    locked_count = sum(1 for p in pay_periods if p.get("status") == PAY_PERIOD_LOCKED)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Open Periods", open_count)
    with col2:
        st.metric("Locked Periods", locked_count)
    
    # Periods table
    table_data = []
    for period in pay_periods:
        table_data.append({
            "Start Date": format_date(period.get("start_date")),
            "End Date": format_date(period.get("end_date")),
            "Status": period.get("status", "open").upper(),
            "Created": format_date(period.get("created_at"))
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Period details and actions
    st.subheader("Period Details")
    period_options = {p["id"]: f"{format_date(p.get('start_date'))} - {format_date(p.get('end_date'))}" for p in pay_periods}
    selected_period_id = st.selectbox("Select Pay Period", list(period_options.keys()), format_func=lambda x: period_options[x])
    
    if selected_period_id:
        selected_period = next((p for p in pay_periods if p["id"] == selected_period_id), None)
        
        if selected_period:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Period:** {format_date(selected_period.get('start_date'))} to {format_date(selected_period.get('end_date'))}")
                st.markdown(f"**Status:** {selected_period.get('status', 'open').upper()}")
            
            with col2:
                if selected_period.get("status") == PAY_PERIOD_OPEN:
                    if st.button("🔒 Lock Period", type="primary", use_container_width=True, key=f"lock_{selected_period_id}"):
                        result = lock_pay_period(selected_period_id, use_service_role=True)
                        if result:
                            st.success("Pay period locked.")
                            st.rerun()
                        else:
                            st.error("Failed to lock period.")
            
            # Pay items for this period
            st.subheader("Pay Items")
            pay_items = get_pay_items_by_period(selected_period_id, use_service_role=True)
            
            if pay_items:
                # Summary
                total_hours = sum(float(item.get("hours", 0)) for item in pay_items)
                total_amount = sum(float(item.get("amount", 0)) for item in pay_items)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Hours", format_duration(total_hours))
                with col2:
                    st.metric("Total Amount", format_currency(total_amount))
                
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
                if st.button("📄 Generate Summary PDF", type="primary"):
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
                            mime="application/pdf"
                        )
            else:
                st.info("No pay items for this period.")
else:
    st.info("No pay periods created yet. Create one to get started.")

