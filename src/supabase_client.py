"""
Supabase client initialization.
"""
from supabase import create_client, Client
from src.config import get_supabase_url, get_supabase_key, validate_config

# Global client instance
_supabase_client: Client | None = None
_supabase_service_client: Client | None = None


def get_client(service_role=False) -> Client:
    """
    Get or create Supabase client instance.
    
    Args:
        service_role: If True, return client with service_role key (admin access).
                     If False, return client with anon key (public access).
    
    Returns:
        Client: Supabase client instance
    """
    global _supabase_client, _supabase_service_client
    
    validate_config()
    
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
        return _supabase_client


def reset_clients():
    """Reset client instances (useful for testing or re-authentication)."""
    global _supabase_client, _supabase_service_client
    _supabase_client = None
    _supabase_service_client = None

