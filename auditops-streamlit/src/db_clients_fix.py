"""
Simple, working client query that matches EXACT database schema.
Replace get_all_clients in db.py with this version.
"""

def get_all_clients(active_only: bool = True):
    """
    Get all clients - EXACT schema match.

    Database schema:
    - client_id (uuid)
    - client_name (text)
    - active (boolean)
    """
    from src.supabase_client import get_client

    client = get_client(service_role=True)

    # Select exact columns from schema
    query = client.table("clients").select("client_id, client_name, active, address, notes")

    if active_only:
        query = query.eq("active", True)

    response = query.order("client_name").execute()

    # Map to expected app format
    result = []
    for row in (response.data or []):
        result.append({
            "id": row["client_id"],
            "name": row["client_name"],
            "is_active": row["active"],
            "address": row.get("address"),
            "notes": row.get("notes")
        })

    return result
