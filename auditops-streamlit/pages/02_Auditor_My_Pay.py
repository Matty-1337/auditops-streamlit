"""
Auditor My Pay - View pay history and statements.
"""
import streamlit as st
from src.pin_auth import require_authentication, require_role, get_current_user
from src.config import ROLE_AUDITOR
from src.db import get_pay_items_by_auditor, get_all_pay_periods
from src.utils import format_date, format_currency, format_duration
from src.pdf_statements import generate_pay_statement_pdf
import pandas as pd

# Page config
st.set_page_config(page_title="My Pay", layout="wide")

# Authentication and role check
require_authentication()
require_role(ROLE_AUDITOR)

# Get current user
user = get_current_user()
auditor_id = user.get('id') if user else None

if not auditor_id:
    st.error("User not found. Please log out and log back in.")
    st.stop()

st.title("💰 My Pay")
st.markdown("View your pay history and download statements.")

# Get pay items
pay_items = get_pay_items_by_auditor(auditor_id)
pay_periods = get_all_pay_periods()

# Summary stats
if pay_items:
    total_hours = sum(float(item.get("hours", 0)) for item in pay_items)
    total_amount = sum(float(item.get("amount", 0)) for item in pay_items)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Hours", format_duration(total_hours))
    with col2:
        st.metric("Total Earnings", format_currency(total_amount))
    with col3:
        st.metric("Pay Items", len(pay_items))

# Filter by pay period
st.subheader("Pay History")
period_options = {None: "All Periods"}
for period in pay_periods:
    period_options[period["id"]] = f"{format_date(period.get('start_date'))} - {format_date(period.get('end_date'))}"

selected_period_id = st.selectbox("Filter by Pay Period", list(period_options.keys()), format_func=lambda x: period_options[x])

# Filter pay items
filtered_items = pay_items
if selected_period_id and selected_period_id != "None":
    filtered_items = [item for item in pay_items if item.get("pay_period", {}).get("id") == selected_period_id]

# Display table
if filtered_items:
    # Prepare data for table
    table_data = []
    for item in filtered_items:
        period = item.get("pay_period") or {}
        shift = item.get("shift") or {}
        
        table_data.append({
            "Pay Period": f"{format_date(period.get('start_date'))} - {format_date(period.get('end_date'))}",
            "Date": format_date(shift.get("check_in")),
            "Hours": f"{float(item.get('hours', 0)):.2f}",
            "Rate": format_currency(item.get("rate")),
            "Amount": format_currency(item.get("amount"))
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Download statement for selected period
    if selected_period_id and selected_period_id != "None":
        st.subheader("Download Statement")
        period = next((p for p in pay_periods if p["id"] == selected_period_id), None)
        period_items = [item for item in pay_items if item.get("pay_period", {}).get("id") == selected_period_id]
        
        if period and period_items:
            profile = st.session_state.get("user_profile", {})
            auditor_name = profile.get("full_name", "Auditor")
            
            if st.button("📄 Generate PDF Statement", type="primary"):
                with st.spinner("Generating PDF..."):
                    pdf_buffer = generate_pay_statement_pdf(
                        auditor_name=auditor_name,
                        pay_period=period,
                        pay_items=period_items
                    )
                    
                    period_label = f"{format_date(period.get('start_date'))}_{format_date(period.get('end_date'))}"
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"pay_statement_{period_label}.pdf",
                        mime="application/pdf"
                    )
else:
    st.info("No pay items found.")

