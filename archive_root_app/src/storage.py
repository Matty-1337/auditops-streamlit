"""
Supabase Storage helpers for file uploads and access logging.
"""
from typing import Optional
from src.supabase_client import get_client
from src.db import create_access_log
from src.auth import get_current_user


def upload_file(bucket: str, file_path: str, file_data: bytes, content_type: Optional[str] = None, use_service_role: bool = True) -> bool:
    """
    Upload a file to Supabase Storage.
    
    Args:
        bucket: Storage bucket name
        file_path: Path within bucket (e.g., "client-docs/client123/doc.pdf")
        file_data: File content as bytes
        content_type: MIME type (optional)
        use_service_role: Use service role key for admin access
    
    Returns:
        bool: True if successful
    """
    try:
        client = get_client(service_role=use_service_role)
        
        options = {}
        if content_type:
            options["content-type"] = content_type
        
        response = client.storage.from_(bucket).upload(file_path, file_data, file_options=options)
        return True
    except Exception as e:
        print(f"Upload failed: {str(e)}")
        return False


def download_file(bucket: str, file_path: str, use_service_role: bool = False) -> Optional[bytes]:
    """
    Download a file from Supabase Storage.
    
    Args:
        bucket: Storage bucket name
        file_path: Path within bucket
        use_service_role: Use service role key if needed
    
    Returns:
        bytes: File content or None if failed
    """
    try:
        client = get_client(service_role=use_service_role)
        response = client.storage.from_(bucket).download(file_path)
        return response
    except Exception as e:
        print(f"Download failed: {str(e)}")
        return None


def get_file_url(bucket: str, file_path: str, expires_in: int = 3600) -> Optional[str]:
    """
    Get a signed URL for a file (temporary access).
    
    Args:
        bucket: Storage bucket name
        file_path: Path within bucket
        expires_in: URL expiration in seconds (default 1 hour)
    
    Returns:
        str: Signed URL or None if failed
    """
    try:
        client = get_client(service_role=False)
        response = client.storage.from_(bucket).create_signed_url(file_path, expires_in)
        return response.get("signedURL")
    except Exception as e:
        print(f"Failed to create signed URL: {str(e)}")
        return None


def log_access(client_id: Optional[str], object_path: str, action: str, ip_optional: Optional[str] = None):
    """
    Log an access event (view/download/upload) to the access_logs table.
    
    Args:
        client_id: Client ID if accessing client-specific document
        object_path: Path to the object accessed
        action: "view", "download", or "upload"
        ip_optional: Optional IP address
    """
    user = get_current_user()
    if not user:
        return
    
    try:
        create_access_log(
            user_id=user.id,
            client_id=client_id,
            object_path=object_path,
            action=action,
            ip_optional=ip_optional,
            use_service_role=True
        )
    except Exception as e:
        print(f"Failed to log access: {str(e)}")


def list_files(bucket: str, folder_path: str = "", use_service_role: bool = False) -> list:
    """
    List files in a storage bucket folder.
    
    Args:
        bucket: Storage bucket name
        folder_path: Folder path within bucket (empty for root)
        use_service_role: Use service role key if needed
    
    Returns:
        list: List of file objects
    """
    try:
        client = get_client(service_role=use_service_role)
        response = client.storage.from_(bucket).list(folder_path)
        return response or []
    except Exception as e:
        print(f"Failed to list files: {str(e)}")
        return []


def delete_file(bucket: str, file_path: str, use_service_role: bool = True) -> bool:
    """
    Delete a file from storage.
    
    Args:
        bucket: Storage bucket name
        file_path: Path to file
        use_service_role: Use service role key for admin access
    
    Returns:
        bool: True if successful
    """
    try:
        client = get_client(service_role=use_service_role)
        client.storage.from_(bucket).remove([file_path])
        return True
    except Exception as e:
        print(f"Delete failed: {str(e)}")
        return False

