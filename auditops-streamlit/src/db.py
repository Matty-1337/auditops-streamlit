"""
Database CRUD operations for all entities.
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from supabase import Client
from src.supabase_client import get_client
from src.config import (
    SHIFT_STATUS_DRAFT, SHIFT_STATUS_SUBMITTED, SHIFT_STATUS_APPROVED, SHIFT_STATUS_REJECTED,
    PAY_PERIOD_OPEN, PAY_PERIOD_LOCKED
)


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


def get_submitted_shifts(use_service_role: bool = False) -> List[Dict]:
    """Get all submitted shifts awaiting approval."""
    import logging
    client = get_client(service_role=use_service_role)

    try:
        response = client.table("shifts").select("*, auditor:profiles(*), client:clients(*)").eq("status", SHIFT_STATUS_SUBMITTED).order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logging.error(f"[DB] get_submitted_shifts failed with joins: {str(e)}")

        # Try without joins
        try:
            logging.info("[DB] Retrying without joins...")
            response = client.table("shifts").select("*").eq("status", SHIFT_STATUS_SUBMITTED).order("created_at", desc=True).execute()
            shifts = response.data or []
            logging.info(f"[DB] Query without joins succeeded, got {len(shifts)} shifts")

            # Manually fetch related data for each shift
            for shift in shifts:
                # Fetch auditor profile
                if shift.get('auditor_id'):
                    try:
                        auditor_response = client.table("profiles").select("*").eq("id", shift['auditor_id']).execute()
                        if auditor_response.data:
                            shift['auditor'] = auditor_response.data[0]
                    except Exception as auditor_err:
                        logging.warning(f"[DB] Could not fetch auditor {shift['auditor_id']}: {auditor_err}")
                        shift['auditor'] = None

                # Fetch client
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
            logging.error(f"[DB] Retry without joins also failed: {str(retry_err)}")

            # Last resort: try with service role if not already using it
            if not use_service_role:
                logging.info("[DB] Retrying with service role...")
                return get_submitted_shifts(use_service_role=True)
            else:
                logging.error("[DB] Service role query also failed, returning empty list")
                return []


def create_shift(data: Dict) -> Optional[Dict]:
    """Create a new shift."""
    client = get_client(service_role=False)
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


def create_pay_period(start_date: date, end_date: date, use_service_role: bool = True) -> Optional[Dict]:
    """Create a new pay period."""
    client = get_client(service_role=use_service_role)
    data = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "status": PAY_PERIOD_OPEN
    }
    response = client.table("pay_periods").insert(data).execute()
    if response.data:
        return response.data[0]
    return None


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

def get_approval(approval_id: str) -> Optional[Dict]:
    """Get approval by ID."""
    client = get_client(service_role=False)
    response = client.table("approvals").select("*, shift:shifts(*), approver:profiles(*)").eq("id", approval_id).execute()
    if response.data:
        return response.data[0]
    return None


def get_approvals_by_shift(shift_id: str) -> List[Dict]:
    """Get approvals for a shift."""
    client = get_client(service_role=False)
    response = client.table("approvals").select("*, approver:profiles(*)").eq("shift_id", shift_id).order("decided_at", desc=True).execute()
    return response.data or []


def create_approval(shift_id: str, approver_id: str, decision: str, notes: Optional[str] = None, use_service_role: bool = False) -> Optional[Dict]:
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
    """Get client secrets by client_id. Relies on RLS."""
    client = get_client(service_role=False)
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
    client = get_client(service_role=False)
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

