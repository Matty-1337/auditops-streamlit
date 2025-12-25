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
    response = client.table("profiles").select("*").eq("id", user_id).execute()
    if response.data:
        return response.data[0]
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
    response = client.table("profiles").update(data).eq("id", user_id).execute()
    if response.data:
        return response.data[0]
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
        client.table("clients_app").select("id").limit(1).execute()
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
    """Get all clients."""
    client = get_client(service_role=False)
    if _check_clients_app_exists():
        query = client.table("clients_app").select("id, name, is_active")
        if active_only:
            query = query.eq("is_active", True)
        response = query.order("name").execute()
        return response.data or []
    else:
        query = client.table("clients").select("*")
        if active_only:
            query = query.eq("active", True)
        response = query.order("client_name").execute()
        return [_normalize_client_row(row) for row in (response.data or [])]


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
    client = get_client(service_role=False)
    query = client.table("shifts").select("*, client:clients(*)").eq("auditor_id", auditor_id)
    if status:
        query = query.eq("status", status)
    response = query.order("check_in", desc=True).execute()
    return response.data or []


def get_submitted_shifts(use_service_role: bool = False) -> List[Dict]:
    """Get all submitted shifts awaiting approval."""
    client = get_client(service_role=use_service_role)
    response = client.table("shifts").select("*, auditor:profiles(*), client:clients(*)").eq("status", SHIFT_STATUS_SUBMITTED).order("created_at", desc=True).execute()
    return response.data or []


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
    client = get_client(service_role=use_service_role)
    response = client.table("pay_items").select("*, pay_period:pay_periods(*), shift:shifts(*)").eq("auditor_id", auditor_id).order("created_at", desc=True).execute()
    return response.data or []


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

