# Authentication Fix Report - Root Cause Analysis & Solution

## Executive Summary

**Status**: CRITICAL BUGS IDENTIFIED  
**Root Cause**: Incorrect `set_session` API usage + potential PKCE flow handling gap  
**Impact**: Magic links and password reset links fail to authenticate users  
**Fix Complexity**: Medium (requires API correction + flow verification)

---

## A) Repository Scan Results

### Authentication-Related Code Locations

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 37-74, 183-206 | JavaScript hash→query conversion, token handling in main() |
| `src/auth.py` | 10-54, 169-293 | Login, logout, token authentication, password reset |
| `src/supabase_client.py` | 12-38 | Supabase client initialization |
| `src/config.py` | 29-81 | Configuration and secrets management |

### Key Functions Found

- ✅ `login()` - Email/password auth (line 10, `src/auth.py`)
- ✅ `authenticate_with_tokens()` - Magic link token handling (line 169, `src/auth.py`)
- ✅ `reset_password()` - Password recovery (line 239, `src/auth.py`)
- ✅ `logout()` - Session cleanup (line 57, `src/auth.py`)
- ❌ **MISSING**: `exchange_code_for_session()` - PKCE code exchange (not found)
- ✅ `set_session()` - Used but **INCORRECTLY** (line 199, `src/auth.py`)

### Session Storage

- **Location**: `st.session_state` (Streamlit session state)
- **Keys**: `auth_user`, `auth_session`, `user_profile`
- **Persistence**: Per-browser session (cleared on refresh unless tokens preserved)

### Query Parameter Handling

- **Current**: Uses `st.query_params` (modern API) ✅
- **Detects**: `access_token`, `refresh_token`, `type`
- **Missing**: `code` parameter detection (for PKCE flow)

---

## B) Auth Flow Mismatch Analysis

### Supabase Magic Link Flow (2024-2025)

**Current Default**: Supabase uses **implicit flow** for magic links (tokens in URL fragment `#access_token=...`)

**Evidence**:
- Supabase documentation confirms magic links use URL fragments
- No PKCE requirement mentioned for email OTP/magic links
- PKCE is primarily for OAuth providers, not email magic links

**What Supabase Returns**:
```
https://auditops.streamlit.app/#access_token=xxx&refresh_token=yyy&type=magiclink
```

### Current App Implementation

**What App Expects**:
- ✅ Hash fragment conversion to query params (JavaScript in `app.py:37-74`)
- ✅ Query param reading (`app.py:184-187`)
- ❌ **INCORRECT**: `set_session(session_dict)` - Wrong API signature

**Mismatch Identified**:
1. **CRITICAL**: `set_session()` API usage is incorrect
   - **Current**: `client.auth.set_session(session_data)` (dict)
   - **Correct**: `client.auth.set_session(access_token, refresh_token)` (two strings)
   - **Impact**: Authentication fails silently or raises TypeError

2. **POTENTIAL**: No PKCE code handling (if Supabase switches to PKCE)
   - Missing `code` parameter detection
   - No `exchange_code_for_session()` call

---

## C) Streamlit Callback Handling Analysis

### Current Implementation Status

✅ **Working**:
- JavaScript converts hash to query params
- Query params are read on app startup
- Session state storage exists

❌ **Broken**:
- `set_session()` API call is incorrect (line 199, `src/auth.py`)
- No error logging for debugging
- No fallback if `set_session()` fails

### Streamlit Rerun Behavior

- ✅ Query params cleared after successful auth (`app.py:201`)
- ✅ `st.rerun()` used correctly
- ⚠️ **Risk**: If `set_session()` fails, user sees login page but no error message

---

## D) Redirect URL Configuration

### Required Supabase Dashboard Settings

**Site URL** (Authentication → URL Configuration):
```
https://auditops.streamlit.app
```

**Additional Redirect URLs**:
```
https://auditops.streamlit.app/*
```

**Current Status**: ⚠️ **UNKNOWN** - Must verify in Supabase dashboard

### Code-Level Redirect Configuration

**Current**: No explicit `redirectTo` parameter in code
- Magic links use Supabase default (Site URL)
- This is correct for Streamlit Cloud deployment

**Verification Needed**:
1. Check Supabase Dashboard → Authentication → URL Configuration
2. Ensure Site URL matches Streamlit Cloud app URL
3. Verify no localhost URLs in redirect list

---

## E) User Creation Sanity Check

### Expected Flow

1. **Create user in Supabase Auth** (Dashboard → Authentication → Users)
2. **Link to profile** (SQL: `INSERT INTO profiles (id, email, full_name, role) VALUES (...)`)
3. **Send magic link** (User clicks link in email)
4. **App authenticates** (Tokens → Session → Profile loaded)

### Potential Issues

**Issue 1**: Users created only in `profiles` table, not in `auth.users`
- **Symptom**: Magic links sent but user doesn't exist in Auth
- **Fix**: Create users via Supabase Auth Dashboard first

**Issue 2**: Profile not linked to Auth user
- **Symptom**: Authentication succeeds but `load_user_profile()` returns None
- **Fix**: Ensure `profiles.id` matches `auth.users.id` (UUID)

**Issue 3**: First-time user onboarding confusion
- **Symptom**: "Reset password" used instead of "Set initial password"
- **Fix**: Use Supabase "Invite User" feature for first-time setup

---

## Root Cause Summary

### Primary Issue (CRITICAL)

**File**: `src/auth.py`, Line 199  
**Problem**: `client.auth.set_session(session_data)` - Incorrect API signature  
**Correct**: `client.auth.set_session(access_token, refresh_token)`  
**Impact**: Authentication fails silently, users stuck in login loop

### Secondary Issues

1. **No error logging**: Failures are silent, hard to debug
2. **No PKCE code handling**: Future-proofing gap (though not currently needed)
3. **Redirect URL verification**: Must confirm Supabase dashboard settings

---

## Implementation Fix

### Fix 1: Correct `set_session()` API Usage

**File**: `src/auth.py`  
**Lines**: 169-236

**Change**:
```python
# BEFORE (WRONG):
response = client.auth.set_session(session_data)

# AFTER (CORRECT):
response = client.auth.set_session(access_token, refresh_token)
```

### Fix 2: Add Error Logging

Add try/except with proper error messages and optional debug logging.

### Fix 3: Add PKCE Code Handling (Future-Proof)

Detect `code` parameter and handle PKCE flow if Supabase switches.

---

## Testing Checklist

- [ ] Magic link authentication works
- [ ] Password reset flow works
- [ ] Session persists across Streamlit reruns
- [ ] Query params cleared after auth
- [ ] Error messages shown on failure
- [ ] Users with profiles can authenticate
- [ ] Users without profiles see appropriate warning

---

## Required Supabase Dashboard Configuration

### Step 1: Verify Redirect URLs

1. Go to Supabase Dashboard → Authentication → URL Configuration
2. Set **Site URL**: `https://auditops.streamlit.app`
3. Add **Additional Redirect URLs**: `https://auditops.streamlit.app/*`

### Step 2: Verify User Creation

1. Go to Authentication → Users
2. Verify all 4 users exist in `auth.users` table
3. For each user, verify UUID matches `profiles.id` in database

### Step 3: Test Magic Link

1. Send test magic link to one user
2. Click link
3. Verify redirect to `https://auditops.streamlit.app#access_token=...`
4. Verify app authenticates successfully

---

## User Onboarding Procedure

### For New Users (First Time)

**Option 1: Invite User (Recommended)**
1. Supabase Dashboard → Authentication → Users → Invite User
2. Enter email, optionally set temporary password
3. User receives invite email
4. User sets password via invite link
5. Create profile: `INSERT INTO profiles (id, email, full_name, role) VALUES (user_uuid, email, name, role)`

**Option 2: Create User + Send Magic Link**
1. Supabase Dashboard → Authentication → Users → Add User
2. Create user with email (no password needed for magic link)
3. Create profile: `INSERT INTO profiles (id, email, full_name, role) VALUES (user_uuid, email, name, role)`
4. Send magic link: `client.auth.sign_in_with_otp({"email": email})`

### For Existing Users

- Use magic link or password login (if password set)
- Use password reset if password forgotten

---

## Next Steps

1. ✅ Apply code fixes (Fix 1-3)
2. ⚠️ Verify Supabase dashboard redirect URLs
3. ⚠️ Verify users exist in `auth.users` (not just `profiles`)
4. ⚠️ Test magic link flow end-to-end
5. ⚠️ Test password reset flow
6. ⚠️ Verify session persistence

