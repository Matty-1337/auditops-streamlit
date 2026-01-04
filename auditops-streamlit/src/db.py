"""
Database CRUD operations for all entities.
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from functools import wraps
import json
import logging
import uuid as uuid_lib
from supabase import Client
from src.supabase_client import get_client
from src.config import (
    SHIFT_STATUS_DRAFT, SHIFT_STATUS_SUBMITTED, SHIFT_STATUS_APPROVED, SHIFT_STATUS_REJECTED,
    PAY_PERIOD_OPEN, PAY_PERIOD_LOCKED
)

# Try to import postgrest exceptions (optional, for enhanced error logging)
try:
    from postgrest.exceptions import APIError
    POSTGREST_EXCEPTIONS_AVAILABLE = True
except ImportError:
    # Fallback: create a dummy APIError class for type hints
    class APIError(Exception):
        pass
    POSTGREST_EXCEPTIONS_AVAILABLE = False


# ============================================
# ERROR LOGGING & MONITORING
# ============================================

def log_postgrest_errors(func):
    """
    Decorator to capture and log full PostgREST errors before Streamlit redacts them.

    This helps diagnose issues by preserving the original error details that would
    otherwise be hidden by Streamlit's security redaction.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            # Extract all available error information
            error_info = {
                "function": func.__name__,
                "args": [str(a)[:100] for a in args],  # Truncate to avoid logging huge objects
                "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
                "error_type": type(e).__name__,
                "error_str": str(e),
                "error_args": e.args if hasattr(e, 'args') else None,
            }

            # Try to extract response details
            if hasattr(e, 'message'):
                error_info["message"] = e.message
            if hasattr(e, 'details'):
                error_info["details"] = e.details
            if hasattr(e, 'hint'):
                error_info["hint"] = e.hint
            if hasattr(e, 'code'):
                error_info["code"] = e.code

            logging.error(f"[PostgREST Error] {json.dumps(error_info, indent=2, default=str)}")

            # Write to file for Streamlit Cloud inspection
            try:
                with open("/tmp/postgrest_errors.log", "a") as f:
                    f.write(json.dumps(error_info, default=str) + "\n")
            except Exception:
                pass

            # Re-raise the original exception
            raise
        except Exception as e:
            # Log non-APIError exceptions too
            logging.exception(f"[DB Error in {func.__name__}] {type(e).__name__}: {str(e)}")
            raise
    return wrapper


def track_api_errors(func):
    """
    Decorator to track API errors for monitoring/alerting.
    Can be extended to send to Sentry, CloudWatch, etc.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Log for monitoring (extend this to push to your monitoring service)
            logging.error(
                f"[MONITOR] API Error in {func.__name__}: {type(e).__name__}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "args_count": len(args),
                }
            )
            # TODO: Uncomment and configure when monitoring service is set up
            # import sentry_sdk
            # sentry_sdk.capture_exception(e)
            raise
    return wrapper


# ============================================
# PROFILES
# ============================================

def get_profile(user_id: str, use_service_role: bool = False) -> Optional[Dict]:
    """Get profile by user ID."""
    client = get_client(service_role=use_service_role)
    try:
        response = (
            client.table("profiles")
            .select("*")
            .eq("user_id", user_id)  # CRITICAL: profiles table uses user_id, not id
            .single()
            .execute()
        )
        # .single() returns the row directly in response.data (not a list)
        if response.data:
            return response.data
        return None
    except Exception:
        # .single() raises exception if no row found
        # Profile not found or query failed
        return None


def get_all_profiles(active_only: bool = True, use_service_role: bool = False) -> List[Dict]:
    """Get all profiles."""
    client = get_client(service_role=use_service_role)
    query = client.table("profiles").select("*")
    if active_only:
        query = query.eq("is_active", True)
    response = query.order("full_name").execute()
    return response.data or []


def create_profile(data: Dict, use_service_role: bool = True) -> Optional[Dict]:
    """Create a new profile. Requires service role."""
    client = get_client(service_role=use_service_role)
    response = client.table("profiles").insert(data).execute()
    if response.data:
        return response.data[0]
    return None


def update_profile(user_id: str, data: Dict, use_service_role: bool = False) -> Optional[Dict]:
    """Update profile."""
    client = get_client(service_role=use_service_role)
    try:
        response = (
            client.table("profiles")
            .update(data)
            .eq("user_id", user_id)  # CRITICAL: profiles table uses user_id, not id
            .single()
            .execute()
        )
        # .single() returns the row directly in response.data (not a list)
        if response.data:
            return response.data
        return None
    except Exception:
        # .single() raises exception if no row found
        # Profile not found or update failed
        return None


# ============================================
# CLIENTS
# ============================================

# Cached helper to detect clients_app view existence
_clients_app_exists = None

def _check_clients_app_exists() -> bool:
    """Check if clients_app view exists. Cached result."""
    global _clients_app_exists
    if _clients_app_exists is not None:
        return _clients_app_exists
    client = get_client(service_role=False)
    try:
        # Schema-agnostic check - doesn't assume id column exists
        client.table("clients_app").select("*").limit(1).execute()
        _clients_app_exists = True
    except Exception:
        _clients_app_exists = False
    return _clients_app_exists


def _normalize_client_row(row: Dict) -> Dict:
    """Normalize client row from clients table to expected format."""
    if "id" in row and "name" in row and "is_active" in row:
        return row
    return {
        "id": row.get("client_id"),
        "name": row.get("client_name"),
        "is_active": row.get("active"),
        **{k: v for k, v in row.items() if k not in ("client_id", "client_name", "active")}
    }


def get_client_by_id(client_id: str) -> Optional[Dict]:
    """Get client by ID."""
    client = get_client(service_role=False)
    if _check_clients_app_exists():
        response = client.table("clients_app").select("id, name, is_active").eq("id", client_id).execute()
        if response.data:
            return response.data[0]
    else:
        response = client.table("clients").select("*").eq("client_id", client_id).execute()
        if response.data:
            return _normalize_client_row(response.data[0])
    return None


def get_all_clients(active_only: bool = True) -> List[Dict]:
    """
    Get all clients from database with full details.

    Database schema:
    - client_id (uuid)
    - client_name (text)
    - active (boolean)
    - address, contact_person, contact_email, contact_phone
    - wifi_name, wifi_password, special_instructions
    - alarm_code, lockbox_code, code_for_lights, cage_lock_code, patio_code
    - audit_day
    """
    client = get_client(service_role=True)

    # Query all client columns
    query = client.table("clients").select("*")

    if active_only:
        query = query.eq("active", True)

    response = query.order("client_name").execute()

    # Map to expected format with all fields
    result = []
    for row in (response.data or []):
        result.append({
            "id": row["client_id"],
            "name": row["client_name"],
            "is_active": row["active"],
            "address": row.get("address"),
            "notes": row.get("notes"),
            "contact_person": row.get("contact_person"),
            "contact_email": row.get("contact_email"),
            "contact_phone": row.get("contact_phone"),
            "wifi_name": row.get("wifi_name"),
            "wifi_password": row.get("wifi_password"),
            "alarm_code": row.get("alarm_code"),
            "lockbox_code": row.get("lockbox_code"),
            "code_for_lights": row.get("code_for_lights"),
            "cage_lock_code": row.get("cage_lock_code"),
            "patio_code": row.get("patio_code"),
            "audit_day": row.get("audit_day"),
            "special_instructions": row.get("special_instructions")
        })

    return result


def create_client(data: Dict, use_service_role: bool = True) -> Optional[Dict]:
    """Create a new client. Requires service role for admin operations."""
    client = get_client(service_role=use_service_role)
    response = client.table("clients").insert(data).execute()
    if response.data:
        return response.data[0]
    return None


def update_client(client_id: str, data: Dict, use_service_role: bool = True) -> Optional[Dict]:
    """Update client."""
    client = get_client(service_role=use_service_role)
    response = client.table("clients").update(data).eq("client_id", client_id).execute()
    if response.data:
        return response.data[0]
    return None


def delete_client(client_id: str, use_service_role: bool = True) -> bool:
    """Soft delete client (set is_active=False)."""
    return update_client(client_id, {"active": False}, use_service_role) is not None


# ============================================
# SHIFTS
# ============================================

def get_shift(shift_id: str) -> Optional[Dict]:
    """Get shift by ID."""
    client = get_client(service_role=False)
    response = client.table("shifts").select("*, auditor:profiles(*), client:clients(*)").eq("id", shift_id).execute()
    if response.data:
        return response.data[0]
    return None


def get_shifts_by_auditor(auditor_id: str, status: Optional[str] = None) -> List[Dict]:
    """Get shifts for an auditor."""
    import logging
    client = get_client(service_role=False)

    try:
        query = client.table("shifts").select("*, client:clients(*)").eq("auditor_id", auditor_id)
        if status:
            query = query.eq("status", status)
        response = query.order("check_in", desc=True).execute()
        return response.data or []
    except Exception as e:
        # Log the actual error for debugging
        logging.error(f"[DB] get_shifts_by_auditor failed for auditor {auditor_id}: {str(e)}")

        # Try without the client join to isolate the issue
        try:
            logging.info("[DB] Retrying query without client join...")
            query = client.table("shifts").select("*").eq("auditor_id", auditor_id)
            if status:
                query = query.eq("status", status)
            response = query.order("check_in", desc=True).execute()

            # If this works, the issue is with the clients table join
            shifts = response.data or []
            logging.info(f"[DB] Query without join succeeded, got {len(shifts)} shifts")

            # Manually fetch client data for each shift
            if shifts:
                for shift in shifts:
                    if shift.get('client_id'):
                        try:
                            client_response = client.table("clients").select("*").eq("id", shift['client_id']).execute()
                            if client_response.data:
                                shift['client'] = client_response.data[0]
                        except Exception as client_err:
                            logging.warning(f"[DB] Could not fetch client {shift['client_id']}: {client_err}")
                            shift['client'] = None

            return shifts
        except Exception as retry_err:
            logging.error(f"[DB] Retry also failed: {str(retry_err)}")
            raise Exception(f"Database query failed. Please check your profile permissions and ensure you have the AUDITOR role set correctly. Error: {str(e)}")


def get_submitted_shifts(use_service_role: bool = True) -> List[Dict]:
    """Get all submitted shifts awaiting approval."""
    import logging
    client = get_client(service_role=use_service_role)

    try:
        # Get shifts without joins first (more reliable)
        response = client.table("shifts").select("*").eq("status", SHIFT_STATUS_SUBMITTED).order("check_in", desc=True).execute()
        shifts = response.data or []
        logging.info(f"[DB] Got {len(shifts)} submitted shifts")

        # Manually fetch related data for each shift
        for shift in shifts:
            # Fetch auditor from app_users table
            if shift.get('auditor_id'):
                try:
                    auditor_response = client.table("app_users").select("id, name, email, phone, role").eq("auth_uuid", shift['auditor_id']).execute()
                    if auditor_response.data and len(auditor_response.data) > 0:
                        shift['auditor'] = auditor_response.data[0]
                    else:
                        shift['auditor'] = None
                        logging.warning(f"[DB] No auditor found for UUID {shift['auditor_id']}")
                except Exception as auditor_err:
                    logging.warning(f"[DB] Could not fetch auditor {shift['auditor_id']}: {auditor_err}")
                    shift['auditor'] = None

            # Fetch client
            if shift.get('client_id'):
                try:
                    client_response = client.table("clients").select("*").eq("client_id", shift['client_id']).execute()
                    if client_response.data and len(client_response.data) > 0:
                        shift['client'] = client_response.data[0]
                    else:
                        shift['client'] = None
                        logging.warning(f"[DB] No client found for ID {shift['client_id']}")
                except Exception as client_err:
                    logging.warning(f"[DB] Could not fetch client {shift['client_id']}: {client_err}")
                    shift['client'] = None

        return shifts
    except Exception as e:
        logging.error(f"[DB] get_submitted_shifts failed: {str(e)}")
        return []


def create_shift(data: Dict) -> Optional[Dict]:
    """Create a new shift."""
    client = get_client(service_role=True)
    if "status" not in data:
        data["status"] = SHIFT_STATUS_DRAFT
    response = client.table("shifts").insert(data).execute()
    if response.data:
        return response.data[0]
    return None


def update_shift(shift_id: str, data: Dict, use_service_role: bool = False) -> Optional[Dict]:
    """Update shift."""
    client = get_client(service_role=use_service_role)
    response = client.table("shifts").update(data).eq("id", shift_id).execute()
    if response.data:
        return response.data[0]
    return None


def submit_shift(shift_id: str) -> Optional[Dict]:
    """Submit shift for approval."""
    return update_shift(shift_id, {"status": SHIFT_STATUS_SUBMITTED})


# ============================================
# PAY PERIODS
# ============================================

def get_pay_period(period_id: str) -> Optional[Dict]:
    """Get pay period by ID."""
    client = get_client(service_role=False)
    response = client.table("pay_periods").select("*").eq("id", period_id).execute()
    if response.data:
        return response.data[0]
    return None


def get_all_pay_periods(use_service_role: bool = False) -> List[Dict]:
    """Get all pay periods."""
    client = get_client(service_role=use_service_role)
    response = client.table("pay_periods").select("*").order("start_date", desc=True).execute()
    return response.data or []


def get_open_pay_periods() -> List[Dict]:
    """Get open (unlocked) pay periods."""
    client = get_client(service_role=False)
    response = client.table("pay_periods").select("*").eq("status", PAY_PERIOD_OPEN).order("start_date", desc=True).execute()
    return response.data or []


@log_postgrest_errors
def create_pay_period(start_date: date, end_date: date, pay_date: Optional[date] = None, use_service_role: bool = True) -> Optional[Dict]:
    """
    Create a new pay period.

    Args:
        start_date: Start date of the pay period (Saturday)
        end_date: End date of the pay period (Friday, 13 days after start)
        pay_date: Pay date (Friday, 7 days after end_date). If None, calculated automatically.
        use_service_role: Whether to use service role (bypasses RLS)

    Returns:
        Created pay period dict or None if failed

    Raises:
        APIError: If database operation fails (e.g., duplicate dates)
    """
    from datetime import timedelta

    client = get_client(service_role=use_service_role)

    # Calculate pay_date if not provided (7 days after end_date)
    if pay_date is None:
        pay_date = end_date + timedelta(days=7)

    # Check for existing pay period with same dates
    try:
        existing = client.table("pay_periods")\
            .select("*")\
            .eq("start_date", start_date.isoformat())\
            .eq("end_date", end_date.isoformat())\
            .execute()

        if existing.data and len(existing.data) > 0:
            logging.warning(f"Pay period already exists for {start_date} to {end_date}")
            return None
    except Exception as e:
        logging.error(f"Error checking for existing pay period: {e}")
        # Continue anyway - the UNIQUE constraint will catch duplicates

    data = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "pay_date": pay_date.isoformat(),
        "status": PAY_PERIOD_OPEN
    }

    try:
        response = client.table("pay_periods").insert(data).execute()
        if response.data:
            logging.info(f"Successfully created pay period: {start_date} to {end_date}, pay date: {pay_date}")
            return response.data[0]
        return None
    except APIError as e:
        # Log detailed error for debugging
        error_msg = str(e)
        logging.error(f"Failed to create pay period: {error_msg}")

        # Check if it's a duplicate key error
        if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
            logging.warning(f"Duplicate pay period detected: {start_date} to {end_date}")
            return None

        # Re-raise for other errors
        raise


def lock_pay_period(period_id: str, use_service_role: bool = True) -> Optional[Dict]:
    """Lock a pay period."""
    return update_pay_period(period_id, {"status": PAY_PERIOD_LOCKED}, use_service_role)


def update_pay_period(period_id: str, data: Dict, use_service_role: bool = True) -> Optional[Dict]:
    """Update pay period."""
    client = get_client(service_role=use_service_role)
    response = client.table("pay_periods").update(data).eq("id", period_id).execute()
    if response.data:
        return response.data[0]
    return None


# ============================================
# PAY ITEMS
# ============================================

def get_pay_items_by_period(period_id: str, auditor_id: Optional[str] = None, use_service_role: bool = False) -> List[Dict]:
    """Get pay items for a pay period, optionally filtered by auditor."""
    client = get_client(service_role=use_service_role)
    query = client.table("pay_items").select("*, auditor:profiles(*), shift:shifts(*)").eq("pay_period_id", period_id)
    if auditor_id:
        query = query.eq("auditor_id", auditor_id)
    response = query.order("created_at").execute()
    return response.data or []


def get_pay_items_by_auditor(auditor_id: str, use_service_role: bool = False) -> List[Dict]:
    """Get all pay items for an auditor."""
    import logging
    client = get_client(service_role=use_service_role)

    try:
        response = client.table("pay_items").select("*, pay_period:pay_periods(*), shift:shifts(*)").eq("auditor_id", auditor_id).order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logging.error(f"[DB] get_pay_items_by_auditor failed with joins: {str(e)}")

        # Try without joins
        try:
            logging.info("[DB] Retrying without joins...")
            response = client.table("pay_items").select("*").eq("auditor_id", auditor_id).order("created_at", desc=True).execute()
            pay_items = response.data or []
            logging.info(f"[DB] Query without joins succeeded, got {len(pay_items)} pay items")

            # Manually fetch related data for each pay item
            for item in pay_items:
                # Fetch pay period
                if item.get('pay_period_id'):
                    try:
                        period_response = client.table("pay_periods").select("*").eq("id", item['pay_period_id']).execute()
                        if period_response.data:
                            item['pay_period'] = period_response.data[0]
                    except Exception as period_err:
                        logging.warning(f"[DB] Could not fetch pay_period {item['pay_period_id']}: {period_err}")
                        item['pay_period'] = None

                # Fetch shift
                if item.get('shift_id'):
                    try:
                        shift_response = client.table("shifts").select("*").eq("id", item['shift_id']).execute()
                        if shift_response.data:
                            item['shift'] = shift_response.data[0]
                    except Exception as shift_err:
                        logging.warning(f"[DB] Could not fetch shift {item['shift_id']}: {shift_err}")
                        item['shift'] = None

            return pay_items
        except Exception as retry_err:
            logging.error(f"[DB] Retry without joins also failed: {str(retry_err)}")

            # Last resort: try with service role if not already using it
            if not use_service_role:
                logging.info("[DB] Retrying with service role...")
                return get_pay_items_by_auditor(auditor_id, use_service_role=True)
            else:
                logging.error("[DB] Service role query also failed, returning empty list")
                return []


def create_pay_item(data: Dict, use_service_role: bool = True) -> Optional[Dict]:
    """Create a pay item."""
    client = get_client(service_role=use_service_role)
    response = client.table("pay_items").insert(data).execute()
    if response.data:
        return response.data[0]
    return None


def create_pay_items_bulk(items: List[Dict], use_service_role: bool = True) -> List[Dict]:
    """Create multiple pay items at once."""
    client = get_client(service_role=use_service_role)
    response = client.table("pay_items").insert(items).execute()
    return response.data or []


# ============================================
# APPROVALS
# ============================================

@log_postgrest_errors
@track_api_errors
def get_approval(approval_id: str) -> Optional[Dict]:
    """
    Get approval by ID with manually fetched related data.

    Fetches approval from database and enriches it with approver and shift data.
    Uses manual fetches instead of foreign key joins to avoid broken relationship errors.

    Args:
        approval_id: The approval ID to retrieve

    Returns:
        Approval dict with nested 'approver' and 'shift' data, or None if not found
    """
    # Validate input
    if not approval_id or not isinstance(approval_id, str):
        logging.warning(f"[DB] Invalid approval_id: {approval_id}")
        return None

    client = get_client(service_role=True)

    try:
        # Get approval without joins first (more reliable)
        response = client.table("approvals").select("*").eq("id", approval_id).execute()
        if not response.data:
            logging.info(f"[DB] No approval found for id={approval_id}")
            return None

        approval = response.data[0]
        logging.info(f"[DB] Retrieved approval {approval_id}")

        # Manually fetch approver from app_users table
        if approval.get('approver_id'):
            try:
                approver_response = client.table("app_users").select("id, name, email, phone, role").eq("auth_uuid", approval['approver_id']).execute()
                if approver_response.data and len(approver_response.data) > 0:
                    approval['approver'] = approver_response.data[0]
                    logging.debug(f"[DB] Fetched approver data for {approval['approver_id']}")
                else:
                    approval['approver'] = None
                    logging.warning(f"[DB] No approver found in app_users for UUID {approval['approver_id']}")
            except Exception as approver_err:
                logging.warning(f"[DB] Could not fetch approver {approval['approver_id']}: {approver_err}")
                approval['approver'] = None

        # Manually fetch shift data
        if approval.get('shift_id'):
            try:
                shift_response = client.table("shifts").select("*").eq("id", approval['shift_id']).execute()
                if shift_response.data and len(shift_response.data) > 0:
                    approval['shift'] = shift_response.data[0]
                    logging.debug(f"[DB] Fetched shift data for {approval['shift_id']}")
                else:
                    approval['shift'] = None
                    logging.warning(f"[DB] No shift found for id {approval['shift_id']}")
            except Exception as shift_err:
                logging.warning(f"[DB] Could not fetch shift {approval['shift_id']}: {shift_err}")
                approval['shift'] = None

        return approval

    except Exception as e:
        logging.exception(f"[DB] get_approval failed for approval_id={approval_id}")
        return None


@log_postgrest_errors
@track_api_errors
def get_approvals_by_shift(shift_id: str, limit: int = 100) -> List[Dict]:
    """
    Get approvals for a shift with manually fetched approver data.

    Fetches approvals from the database and manually enriches with approver data
    from app_users table to avoid broken foreign key joins to profiles table.

    Args:
        shift_id: The shift ID to get approvals for
        limit: Maximum number of approvals to return (default 100, prevents huge payloads)

    Returns:
        List of approval dicts with nested 'approver' data, or empty list on error
    """
    # Validate input
    if not shift_id or not isinstance(shift_id, str):
        logging.warning(f"[DB] Invalid shift_id: {shift_id}")
        return []

    # Validate shift_id format (if it should be a UUID)
    try:
        uuid_lib.UUID(shift_id)
    except (ValueError, AttributeError, TypeError):
        # Not a UUID - could be integer or other format
        # Log for debugging but continue (some systems use int IDs)
        logging.debug(f"[DB] shift_id {shift_id} is not a UUID format")

    client = get_client(service_role=True)

    try:
        # Get approvals without joins first (more reliable)
        # Add limit to prevent huge payloads
        response = client.table("approvals").select("*").eq("shift_id", shift_id).order("created_at", desc=True).limit(limit).execute()
        approvals = response.data or []
        logging.info(f"[DB] Got {len(approvals)} approvals for shift {shift_id}")

        # Manually fetch approver data for each approval
        for approval in approvals:
            if approval.get('approver_id'):
                try:
                    # Query app_users by auth_uuid (not profiles table)
                    approver_response = client.table("app_users").select("id, name, email, phone, role").eq("auth_uuid", approval['approver_id']).execute()
                    if approver_response.data and len(approver_response.data) > 0:
                        approval['approver'] = approver_response.data[0]
                        logging.debug(f"[DB] Fetched approver {approval['approver_id']}")
                    else:
                        approval['approver'] = None
                        logging.warning(f"[DB] No approver found in app_users for UUID {approval['approver_id']}")
                except Exception as approver_err:
                    logging.warning(f"[DB] Could not fetch approver {approval['approver_id']}: {approver_err}")
                    approval['approver'] = None
            else:
                approval['approver'] = None

        return approvals

    except Exception as e:
        # Log full error details for diagnosis
        logging.exception(f"[DB] get_approvals_by_shift failed for shift_id={shift_id}")

        # Return empty list rather than crashing the app
        # The UI will show "No previous decisions" which is acceptable fallback
        return []


def create_approval(shift_id: str, approver_id: str, decision: str, notes: Optional[str] = None, use_service_role: bool = True) -> Optional[Dict]:
    """Create an approval decision."""
    client = get_client(service_role=use_service_role)
    data = {
        "shift_id": shift_id,
        "approver_id": approver_id,
        "decision": decision,
        "decision_notes": notes
    }
    response = client.table("approvals").insert(data).execute()
    if response.data:
        # Update shift status
        new_status = SHIFT_STATUS_APPROVED if decision == "approved" else SHIFT_STATUS_REJECTED
        update_shift(shift_id, {"status": new_status}, use_service_role=use_service_role)
        return response.data[0]
    return None


def diagnose_approvals_query(shift_id: str) -> Dict:
    """
    Run progressive query tests to isolate approval query failures.

    This diagnostic function tests various query patterns to identify
    the exact cause of APIErrors when fetching approvals.

    Args:
        shift_id: The shift ID to test queries against

    Returns:
        Dict with test results for each query variant
    """
    client = get_client(service_role=True)
    results = {}

    # Test 1: Minimal query (no joins, no order)
    try:
        response = client.table("approvals").select("*").eq("shift_id", shift_id).limit(1).execute()
        results["test_1_minimal"] = {
            "status": "✅ PASS",
            "rows": len(response.data),
            "description": "Basic query without joins or ordering"
        }
    except APIError as e:
        results["test_1_minimal"] = {
            "status": "❌ FAIL",
            "error": str(e.args),
            "description": "Basic query without joins or ordering"
        }

    # Test 2: With profiles join (expected to fail if FK is broken)
    try:
        response = client.table("approvals").select("*, approver:profiles(*)").eq("shift_id", shift_id).limit(1).execute()
        results["test_2_profiles_join"] = {
            "status": "✅ PASS",
            "rows": len(response.data),
            "description": "Query with approver:profiles(*) join"
        }
    except APIError as e:
        results["test_2_profiles_join"] = {
            "status": "❌ FAIL",
            "error": str(e.args),
            "description": "Query with approver:profiles(*) join - FK likely broken"
        }

    # Test 3: Explicit profile fields (smaller payload)
    try:
        response = client.table("approvals").select("*, approver:profiles(id,full_name,email)").eq("shift_id", shift_id).limit(1).execute()
        results["test_3_explicit_fields"] = {
            "status": "✅ PASS",
            "rows": len(response.data),
            "description": "Query with explicit profile fields"
        }
    except APIError as e:
        results["test_3_explicit_fields"] = {
            "status": "❌ FAIL",
            "error": str(e.args),
            "description": "Query with explicit profile fields"
        }

    # Test 4: Manual fetch from app_users (recommended approach)
    try:
        response = client.table("approvals").select("*").eq("shift_id", shift_id).limit(1).execute()
        if response.data:
            approval = response.data[0]
            approver_id = approval.get('approver_id')
            # Try to fetch from app_users
            user_response = client.table("app_users").select("*").eq("auth_uuid", approver_id).execute()
            results["test_4_app_users_manual"] = {
                "status": "✅ PASS",
                "approver_found": len(user_response.data) > 0,
                "description": "Manual fetch from app_users table"
            }
        else:
            results["test_4_app_users_manual"] = {
                "status": "⏭️ SKIPPED",
                "reason": "No approvals found for this shift",
                "description": "Manual fetch from app_users table"
            }
    except Exception as e:
        results["test_4_app_users_manual"] = {
            "status": "❌ FAIL",
            "error": str(e),
            "description": "Manual fetch from app_users table"
        }

    # Test 5: Check for type mismatch (UUID vs int)
    try:
        # Check if shift_id looks like a UUID
        is_uuid = False
        try:
            uuid_lib.UUID(shift_id)
            is_uuid = True
        except (ValueError, AttributeError):
            pass

        if is_uuid:
            response = client.table("approvals").select("*").eq("shift_id", shift_id).limit(1).execute()
            results["test_5_type_check"] = {
                "status": "✅ PASS",
                "shift_id_type": "UUID",
                "description": "Shift ID type validation"
            }
        else:
            results["test_5_type_check"] = {
                "status": "ℹ️ INFO",
                "shift_id_type": "Non-UUID (possibly integer or string)",
                "description": "Shift ID type validation"
            }
    except Exception as e:
        results["test_5_type_check"] = {
            "status": "❌ FAIL",
            "error": str(e),
            "description": "Shift ID type validation"
        }

    # Test 6: Without order clause to test if ordering triggers error
    try:
        response = client.table("approvals").select("*").eq("shift_id", shift_id).execute()
        results["test_6_no_ordering"] = {
            "status": "✅ PASS",
            "rows": len(response.data),
            "description": "Query without order clause"
        }
    except APIError as e:
        results["test_6_no_ordering"] = {
            "status": "❌ FAIL",
            "error": str(e.args),
            "description": "Query without order clause"
        }

    logging.info(f"[DIAGNOSTIC] Approval query test results:\n{json.dumps(results, indent=2, default=str)}")
    return results


# ============================================
# ACCESS LOGS
# ============================================

def create_access_log(user_id: str, client_id: Optional[str], object_path: str, action: str, ip_optional: Optional[str] = None, use_service_role: bool = True) -> Optional[Dict]:
    """Create an access log entry."""
    client = get_client(service_role=use_service_role)
    data = {
        "user_id": user_id,
        "client_id": client_id,
        "object_path": object_path,
        "action": action,
        "ip_optional": ip_optional
    }
    response = client.table("access_logs").insert(data).execute()
    if response.data:
        return response.data[0]
    return None


def get_access_logs(client_id: Optional[str] = None, user_id: Optional[str] = None, limit: int = 100, use_service_role: bool = True) -> List[Dict]:
    """Get access logs with optional filters."""
    client = get_client(service_role=use_service_role)
    query = client.table("access_logs").select("*, user:profiles(*), client:clients(*)")
    
    if client_id:
        query = query.eq("client_id", client_id)
    if user_id:
        query = query.eq("user_id", user_id)
    
    response = query.order("created_at", desc=True).limit(limit).execute()
    return response.data or []


# ============================================
# CLIENT SECRETS
# ============================================

def get_client_secrets(client_id: str) -> Optional[Dict]:
    """Get client secrets by client_id. Auditors need access to site information."""
    client = get_client(service_role=True)  # Use service role so auditors can access
    try:
        response = client.table("client_secrets").select(
            "wifi_name, wifi_password, alarm_code, lockbox_code, other_site_notes"
        ).eq("client_id", client_id).limit(1).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception:
        return None


def log_secrets_access(client_id: str, auditor_user_id: str, fields_accessed: List[str], reason: Optional[str] = None) -> bool:
    """Log secrets access. Returns True on success, False on failure."""
    client = get_client(service_role=True)  # Use service role to log access
    try:
        # fields_accessed is jsonb, so keep as list
        data = {
            "client_id": client_id,
            "auditor_user_id": auditor_user_id,
            "fields_accessed": fields_accessed,
            "reason": reason
        }
        response = client.table("secrets_access_log").insert(data).execute()
        return bool(response.data)
    except Exception:
        return False

