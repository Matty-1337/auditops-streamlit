# Authentication Fix - Code Changes Summary

## Root Cause

**CRITICAL BUG**: `set_session()` API was called incorrectly with a dictionary instead of two separate parameters.

**Location**: `src/auth.py`, line 199 (original)

**Impact**: All magic link and password reset authentications failed silently.

---

## Files Modified

### 1. `src/auth.py`

#### Change 1: Fix `authenticate_with_tokens()` function (Lines 169-236)

**BEFORE**:
```python
session_data = {
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer",
    "expires_in": 3600,
    "expires_at": expires_at
}
response = client.auth.set_session(session_data)
```

**AFTER**:
```python
# CRITICAL FIX: supabase-py set_session takes access_token and refresh_token as separate parameters
try:
    response = client.auth.set_session(access_token, refresh_token)
except TypeError:
    # Fallback for older API versions
    session_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 3600
    }
    response = client.auth.set_session(session_data)
```

**Also Added**:
- Error logging for debugging
- Better error messages
- Graceful handling of missing session object

#### Change 2: Fix `reset_password()` function (Lines 254-266)

**BEFORE**:
```python
session_data = {...}
client.auth.set_session(session_data)
```

**AFTER**:
```python
client.auth.set_session(access_token, refresh_token)
```

---

### 2. `app.py`

#### Change 1: Add PKCE code handling (Lines 185-213)

**ADDED**:
```python
auth_code = query_params.get("code")  # PKCE flow (if Supabase switches)

# Handle PKCE code exchange (if code present, exchange for session)
if auth_code and not is_authenticated():
    try:
        client = get_client(service_role=False)
        response = client.auth.exchange_code_for_session(auth_code)
        # ... handle response
    except Exception:
        # Fall through to token flow
        pass
```

**Purpose**: Future-proofing for PKCE flow (though not currently used by Supabase magic links)

#### Change 2: Add imports (Lines 6-11)

**ADDED**:
```python
from src.auth import load_user_profile
from src.supabase_client import get_client
```

---

## Authentication Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER CLICKS MAGIC LINK                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Supabase redirects to:                                      │
│  https://auditops.streamlit.app/#access_token=xxx&...        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  JavaScript (app.py:37-74) converts hash to query params:   │
│  #access_token=xxx → ?access_token=xxx                      │
│  Then reloads page                                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Streamlit app.py:main() detects tokens in query params     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  authenticate_with_tokens() called                          │
│  client.auth.set_session(access_token, refresh_token) ✅     │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Session stored in st.session_state:                        │
│  - auth_user                                                │
│  - auth_session                                             │
│  - user_profile (loaded from database)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Query params cleared, st.rerun() called                    │
│  User sees main app (authenticated)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Instructions

### 1. Test Magic Link Authentication

1. **Send magic link**:
   ```python
   # In Supabase Dashboard or via API
   client.auth.sign_in_with_otp({"email": "user@example.com"})
   ```

2. **Click link in email** → Should redirect to app with tokens

3. **Verify**:
   - ✅ App shows "Authenticating..." spinner
   - ✅ User is logged in (sees main app, not login page)
   - ✅ Query params are cleared from URL
   - ✅ Session persists on page refresh

### 2. Test Password Reset

1. **Request password reset**:
   ```python
   client.auth.reset_password_for_email("user@example.com")
   ```

2. **Click reset link** → Should show password reset form

3. **Set new password** → Should authenticate and redirect

### 3. Verify Error Handling

1. **Expired token**: Should show "link may have expired" message
2. **Invalid token**: Should show authentication failed message
3. **No profile**: Should show "profile not found" warning

---

## Required Supabase Dashboard Configuration

### Authentication → URL Configuration

**Site URL**:
```
https://auditops.streamlit.app
```

**Additional Redirect URLs**:
```
https://auditops.streamlit.app/*
```

**Important**: Remove any `localhost` URLs if present.

### Verify Users Exist

1. Go to **Authentication → Users**
2. Verify all 4 users exist in `auth.users` table
3. For each user, check:
   - UUID matches `profiles.id` in database
   - Email matches `profiles.email`
   - User is confirmed (not pending)

### Create Missing Profiles

If users exist in Auth but not in profiles:

```sql
-- Get user UUID from Supabase Dashboard → Authentication → Users
INSERT INTO profiles (id, email, full_name, role)
VALUES (
    'user-uuid-from-auth',
    'user@example.com',
    'User Name',
    'AUDITOR'  -- or 'ADMIN', 'MANAGER'
);
```

---

## User Onboarding Procedure

### For New Users

**Recommended: Invite User Flow**

1. **Supabase Dashboard** → Authentication → Users → **Invite User**
2. Enter email, optionally set temporary password
3. User receives invite email
4. User clicks invite link → Sets password
5. **Create profile**:
   ```sql
   SELECT bootstrap_first_admin(
       '<user-uuid-from-auth>',
       'user@example.com',
       'User Name'
   );
   ```
   Or for non-admin:
   ```sql
   INSERT INTO profiles (id, email, full_name, role)
   VALUES ('<user-uuid>', 'user@example.com', 'User Name', 'AUDITOR');
   ```

### For Existing Users (Password Reset)

1. User clicks "Forgot Password" (if implemented)
2. Or admin sends reset: `client.auth.reset_password_for_email(email)`
3. User clicks reset link → Sets new password
4. User is authenticated automatically

---

## Troubleshooting

### Issue: "Authentication failed" error

**Check**:
1. Tokens in URL? (Should see `?access_token=...&refresh_token=...`)
2. Supabase redirect URLs configured correctly?
3. User exists in `auth.users`?
4. Profile exists in `profiles` table?

**Debug**:
- Check browser console for JavaScript errors
- Check Streamlit logs for Python errors
- Verify `set_session()` is being called with correct parameters

### Issue: User authenticated but no profile

**Fix**:
```sql
INSERT INTO profiles (id, email, full_name, role)
VALUES ('<auth-user-uuid>', '<email>', '<name>', '<role>');
```

### Issue: Magic link redirects to wrong URL

**Fix**:
1. Check Supabase Dashboard → Authentication → URL Configuration
2. Ensure Site URL is `https://auditops.streamlit.app`
3. Add `https://auditops.streamlit.app/*` to Additional Redirect URLs

---

## Code Quality Notes

- ✅ Error logging added for debugging
- ✅ Graceful fallbacks for API version differences
- ✅ No breaking changes to existing flows
- ✅ Future-proofed for PKCE flow
- ✅ Security: Tokens not exposed in error messages
- ✅ Query params cleared after use

---

## Next Steps After Deployment

1. ✅ Test magic link authentication
2. ✅ Test password reset flow
3. ✅ Verify session persistence
4. ✅ Check error handling
5. ✅ Verify all 4 users can authenticate
6. ✅ Monitor logs for any authentication errors

