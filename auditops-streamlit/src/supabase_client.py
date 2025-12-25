"""
Supabase client initialization.
"""
import streamlit as st
from supabase import create_client, Client
from src.config import get_supabase_url, get_supabase_key, validate_config

# Global client instance
_supabase_client: Client | None = None
_supabase_service_client: Client | None = None


def get_client(service_role=False) -> Client:
    """
    Get or create Supabase client instance.
    Rehydrates session from st.session_state if available.
    
    Args:
        service_role: If True, return client with service_role key (admin access).
                     If False, return client with anon key (public access).
    
    Returns:
        Client: Supabase client instance with session rehydrated if available
    """
    global _supabase_client, _supabase_service_client
    
    # Validate config (only checks if secrets exist, not database connectivity)
    # This should not block if secrets are present, even if DB queries fail
    try:
        validate_config()
    except ValueError:
        # Re-raise config errors (missing secrets) - these are critical
        raise
    
    url = get_supabase_url()
    
    if service_role:
        if _supabase_service_client is None:
            key = get_supabase_key(service_role=True)
            _supabase_service_client = create_client(url, key)
        return _supabase_service_client
    else:
        if _supabase_client is None:
            key = get_supabase_key(service_role=False)
            _supabase_client = create_client(url, key)
        
        # CRITICAL FIX: Rehydrate session from st.session_state on every call
        # This ensures the client has the session even after reruns
        # Only rehydrate if client doesn't already have a valid session (prevents unnecessary calls)
        if _supabase_client and "auth_session" in st.session_state:
            session = st.session_state.auth_session
            if session:
                # Check if client already has a valid session to avoid unnecessary rehydration
                needs_rehydration = True
                try:
                    current_user = _supabase_client.auth.get_user()
                    user_obj = current_user.user if hasattr(current_user, "user") else current_user
                    if user_obj and hasattr(user_obj, "id"):
                        # Client has valid session, check if it matches stored user
                        stored_user = st.session_state.get("auth_user")
                        if stored_user:
                            stored_id = getattr(stored_user, "id", None) if hasattr(stored_user, "id") else None
                            if stored_id and user_obj.id == stored_id:
                                needs_rehydration = False  # Session already valid and matches
                except Exception:
                    # Client has no session or error, needs rehydration
                    pass
                
                if needs_rehydration:
                    # Extract tokens from session object
                    access_token = None
                    refresh_token = None
                    
                    if hasattr(session, "access_token"):
                        access_token = session.access_token
                    elif hasattr(session, "token"):
                        access_token = session.token
                    elif isinstance(session, dict):
                        access_token = session.get("access_token")
                    
                    if hasattr(session, "refresh_token"):
                        refresh_token = session.refresh_token
                    elif isinstance(session, dict):
                        refresh_token = session.get("refresh_token")
                    
                    # Rehydrate client with stored session tokens
                    if access_token and refresh_token:
                        try:
                            _supabase_client.auth.set_session(access_token, refresh_token)
                        except (TypeError, AttributeError):
                            # Fallback for different API versions
                            try:
                                session_dict = {
                                    "access_token": access_token,
                                    "refresh_token": refresh_token,
                                    "token_type": "bearer"
                                }
                                _supabase_client.auth.set_session(session_dict)
                            except Exception:
                                # If rehydration fails, continue anyway
                                # The session might still be valid in the client
                                pass
        
        return _supabase_client


def reset_clients():
    """Reset client instances (useful for testing or re-authentication)."""
    global _supabase_client, _supabase_service_client
    _supabase_client = None
    _supabase_service_client = None

