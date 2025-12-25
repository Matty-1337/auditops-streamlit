import os
import sys
import argparse
import requests

def _require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def _headers(service_role_key: str) -> dict:
    return {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
        "Content-Type": "application/json",
    }

def list_users(supabase_url: str, service_role_key: str, per_page: int = 200) -> list:
    url = f"{supabase_url.rstrip('/')}/auth/v1/admin/users?per_page={per_page}"
    r = requests.get(url, headers=_headers(service_role_key), timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("users", [])

def find_user_id_by_email(supabase_url: str, service_role_key: str, email: str) -> str | None:
    users = list_users(supabase_url, service_role_key)
    match = next((u for u in users if (u.get("email") or "").lower() == email.lower()), None)
    return match.get("id") if match else None

def create_user(supabase_url: str, service_role_key: str, email: str, password: str, email_confirm: bool = True) -> str:
    url = f"{supabase_url.rstrip('/')}/auth/v1/admin/users"
    payload = {
        "email": email,
        "password": password,
        "email_confirm": email_confirm,
    }
    r = requests.post(url, headers=_headers(service_role_key), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["id"]

def update_user_password(supabase_url: str, service_role_key: str, user_id: str, password: str) -> None:
    url = f"{supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    payload = {"password": password}
    r = requests.put(url, headers=_headers(service_role_key), json=payload, timeout=30)
    r.raise_for_status()

def upsert_user_password(supabase_url: str, service_role_key: str, email: str, password: str, email_confirm: bool = True) -> tuple[str, str]:
    """
    Returns (status, user_id) where status is 'created' or 'updated_password'
    """
    # Try create first
    try:
        user_id = create_user(supabase_url, service_role_key, email, password, email_confirm=email_confirm)
        return ("created", user_id)
    except requests.HTTPError as e:
        # Supabase returns 422 for existing user (commonly). Handle by searching and updating.
        resp = getattr(e, "response", None)
        text = (resp.text if resp is not None else str(e)).lower()
        if resp is not None and resp.status_code in (400, 409, 422) and "already" in text:
            user_id = find_user_id_by_email(supabase_url, service_role_key, email)
            if not user_id:
                raise RuntimeError(f"User appears to exist but could not be found by email: {email}")
            update_user_password(supabase_url, service_role_key, user_id, password)
            return ("updated_password", user_id)
        raise

def main():
    parser = argparse.ArgumentParser(description="Create a Supabase Auth user or update their password (ADMIN).")
    parser.add_argument("--email", help="User email")
    parser.add_argument("--password", help="User password")
    parser.add_argument("--no-confirm", action="store_true", help="Do not auto-confirm email")
    args = parser.parse_args()

    supabase_url = _require_env("SUPABASE_URL")
    service_role_key = _require_env("SUPABASE_SERVICE_ROLE_KEY")

    email = args.email or input("Email: ").strip()
    password = args.password or input("Password: ").strip()
    email_confirm = not args.no_confirm

    if not email or not password:
        raise RuntimeError("Email and password are required.")

    status, user_id = upsert_user_password(
        supabase_url=supabase_url,
        service_role_key=service_role_key,
        email=email,
        password=password,
        email_confirm=email_confirm
    )

    print(f"✅ Success: {status} for {email} (user_id={user_id})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

