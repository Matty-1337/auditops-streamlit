"""
Common utility functions for date formatting, UI helpers, etc.
"""
from datetime import datetime, date, timedelta
from typing import Optional
import streamlit as st


def format_datetime(dt: Optional[datetime | str], format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime to string."""
    if dt is None:
        return "—"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    
    return str(dt)


def format_date(d: Optional[date | str], format_str: str = "%Y-%m-%d") -> str:
    """Format date to string."""
    if d is None:
        return "—"
    
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            return d
    
    if isinstance(d, date):
        return d.strftime(format_str)
    
    return str(d)


def format_currency(amount: Optional[float | str], currency: str = "$") -> str:
    """Format amount as currency."""
    if amount is None:
        return f"{currency}0.00"
    
    try:
        amount = float(amount)
        return f"{currency}{amount:,.2f}"
    except (ValueError, TypeError):
        return f"{currency}0.00"


def format_duration(hours: Optional[float]) -> str:
    """Format hours as duration (e.g., '8h 30m')."""
    if hours is None or hours == 0:
        return "0h"
    
    try:
        hours = float(hours)
        h = int(hours)
        m = int((hours - h) * 60)
        if m > 0:
            return f"{h}h {m}m"
        return f"{h}h"
    except (ValueError, TypeError):
        return "0h"


def calculate_hours(check_in: datetime, check_out: Optional[datetime]) -> Optional[float]:
    """Calculate hours between check-in and check-out."""
    if check_out is None:
        return None
    
    if isinstance(check_in, str):
        check_in = datetime.fromisoformat(check_in.replace("Z", "+00:00"))
    if isinstance(check_out, str):
        check_out = datetime.fromisoformat(check_out.replace("Z", "+00:00"))
    
    delta = check_out - check_in
    return delta.total_seconds() / 3600.0


def get_pay_period_dates(period_type: str = "biweekly", start_date: Optional[date] = None) -> tuple[date, date]:
    """
    Get start and end dates for a pay period.
    
    Args:
        period_type: "biweekly" or "monthly"
        start_date: Start date (defaults to today)
    
    Returns:
        tuple: (start_date, end_date)
    """
    if start_date is None:
        start_date = date.today()
    
    if period_type == "biweekly":
        end_date = start_date + timedelta(days=13)  # 14-day period
    else:  # monthly
        # First day of month to last day
        if start_date.day == 1:
            # Calculate last day of month
            if start_date.month == 12:
                end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
        else:
            # Use current month
            if start_date.month == 12:
                end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date


def render_status_badge(status: str, status_map: Optional[dict] = None):
    """Render a status badge with color."""
    if status_map is None:
        status_map = {
            "draft": ("⚪", "gray"),
            "submitted": ("🟡", "orange"),
            "approved": ("🟢", "green"),
            "rejected": ("🔴", "red"),
            "open": ("🟢", "green"),
            "locked": ("🔒", "gray"),
        }
    
    emoji, color = status_map.get(status.lower(), ("⚪", "gray"))
    st.markdown(f"{emoji} **{status.upper()}**")


def render_table_with_filters(df, key_prefix: str = "table"):
    """Render a dataframe with search/filter capabilities."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search = st.text_input("🔍 Search", key=f"{key_prefix}_search", placeholder="Search...")
    
    with col2:
        show_all = st.checkbox("Show all", value=False, key=f"{key_prefix}_show_all")
    
    if search:
        # Simple text search across all columns
        mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        df = df[mask]
    
    st.dataframe(df, use_container_width=True, hide_index=True)
    return df


def get_client_display_name(client: Optional[dict]) -> str:
    """Get display name for a client."""
    if not client:
        return "—"
    if isinstance(client, dict):
        # Try both 'client_name' (database field) and 'name' (mapped field)
        return client.get("client_name", client.get("name", "Unknown"))
    return str(client)


def get_user_display_name(profile: Optional[dict]) -> str:
    """Get display name for a user profile."""
    if not profile:
        return "—"
    if isinstance(profile, dict):
        # Try 'name' (app_users field) first, then 'full_name' (profiles field), then fallback to email
        return profile.get("name", profile.get("full_name", profile.get("email", "Unknown")))
    return str(profile)

