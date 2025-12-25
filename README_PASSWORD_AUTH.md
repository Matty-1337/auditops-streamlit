# Password-First Authentication Setup

This document explains how to configure and use password-based authentication for the AuditOps Streamlit app.

## Overview

The app uses **password-first authentication** via Supabase Auth. Users log in with email and password. Magic link authentication is deprecated in favor of this more reliable method for Streamlit Cloud.

---

## Streamlit Secrets Configuration

The Streamlit app requires **ONLY** the anon key. **NEVER** put the service role key in Streamlit secrets.

### Required Secrets (`.streamlit/secrets.toml` or Streamlit Cloud secrets)

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_ANON_KEY = "your_anon_key_here"
```

**Important**: 
- ✅ Use `SUPABASE_ANON_KEY` (public key)
- ❌ **DO NOT** use `SUPABASE_SERVICE_ROLE_KEY` in Streamlit secrets
- The service role key is only used in local admin tools

---

## Admin Tool: Setting User Passwords

The admin tool (`tools/admin_set_password.py`) allows you to create users or update their passwords using the Supabase Admin API. This tool **MUST** be run locally on your machine, never in Streamlit Cloud.

### Prerequisites

1. Python 3.8+ installed
2. `requests` library installed (already in `requirements.txt`)
3. Access to your Supabase service role key (found in Supabase Dashboard → Settings → API)

### Running the Admin Tool

#### Windows PowerShell

```powershell
# Set environment variables
$env:SUPABASE_URL="https://xxxx.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="your_service_role_key_here"

# Run with command-line arguments
python tools/admin_set_password.py --email "user@example.com" --password "TempPass123!"

# Or run interactively (will prompt for email and password)
python tools/admin_set_password.py
```

#### macOS/Linux

```bash
# Set environment variables
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key_here"

# Run with command-line arguments
python tools/admin_set_password.py --email "user@example.com" --password "TempPass123!"

# Or run interactively (will prompt for email and password)
python tools/admin_set_password.py
```

### Admin Tool Options

- `--email`: User email address (required)
- `--password`: User password (required)
- `--no-confirm`: Do not auto-confirm email (default: email is auto-confirmed)

### Example Output

```
✅ Success: created for user@example.com (user_id=abc123-def456-ghi789)
```

or

```
✅ Success: updated_password for user@example.com (user_id=abc123-def456-ghi789)
```

---

## Recommended Onboarding Policy

1. **Admin creates user with temporary password**:
   ```bash
   python tools/admin_set_password.py --email "newuser@example.com" --password "TempPass123!"
   ```

2. **Admin sends temporary password to user securely** (email, secure message, etc.)

3. **User logs in** with temporary password via Streamlit app

4. **User changes password** (optional future enhancement: add "Change Password" page in app)

---

## User Login Flow

1. User navigates to Streamlit app
2. User enters email and password
3. App calls `supabase.auth.sign_in_with_password()`
4. On success:
   - Session stored in `st.session_state`
   - User profile loaded
   - User redirected to main app
5. On failure:
   - Error message displayed
   - User can try again or use "Forgot Password"

---

## Forgot Password Flow (Optional)

Users can click "Forgot Password?" on the login page to:
1. Enter their email address
2. Receive a password reset link via email
3. Click link to reset password (redirects to password reset form)

**Note**: This uses Supabase's password reset email, which may redirect to the app. The app handles this callback but password login remains the primary method.

---

## Security Notes

- ✅ Service role key is **NEVER** used in Streamlit runtime
- ✅ Service role key is **ONLY** used in local admin scripts
- ✅ All authentication uses anon key (public key)
- ✅ Passwords are never logged or exposed
- ✅ Session tokens are stored securely in `st.session_state`

---

## Troubleshooting

### "Invalid email or password" error

- Verify user exists in Supabase Auth (check Supabase Dashboard)
- Verify password is correct
- Check if email is confirmed (admin tool auto-confirms by default)

### "User profile not found" error

- User exists in Supabase Auth but not in `profiles` table
- Admin must create profile record in database
- See `sql/schema.sql` for profile structure

### Admin tool fails

- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` environment variables are set
- Verify service role key is correct (from Supabase Dashboard)
- Check network connectivity to Supabase API

---

## Migration from Magic Link Auth

If you previously used magic link authentication:

1. ✅ Password login is now the primary method
2. ✅ Magic link callbacks are still handled (for password reset emails)
3. ✅ All existing users can log in with password (if password is set)
4. ✅ Use admin tool to set passwords for existing users

---

## Files Reference

- **Login UI**: `app.py` - `show_login_page()` function
- **Password Auth**: `src/auth.py` - `login()` function
- **Admin Tool**: `tools/admin_set_password.py`
- **Config**: `src/config.py` - Supabase configuration

