# Drift Sync Report: Root vs Nested Production Files

**Generated:** 2025-01-27  
**Purpose:** Identify and classify differences between root and nested (production) app trees

## Executive Summary

Production runs from `auditops-streamlit/` directory, but many critical fixes were applied to root files. This report classifies differences and identifies what must be ported to production.

---

## File-by-File Comparison

### 1. `app.py` (Root vs `auditops-streamlit/app.py`)

#### MUST PORT (Security/Auth Correctness):
- **Structured login result handling** (lines 145-168 in root):
  - Root properly handles structured `{"ok", "auth_ok", "profile_ok", "error"}` result
  - Nested only checks `if result:` which fails with structured dict
  - **Impact:** Login UI shows wrong error messages or fails silently

- **Session rehydration logic** (lines 418-445 in root):
  - Root rehydrates Supabase client session from `st.session_state` before auth check
  - Nested missing this - sessions lost between reruns
  - **Impact:** Users logged out unexpectedly on page refresh

#### SHOULD PORT (Important UX):
- **JavaScript fragment-to-query conversion** (lines 47-115 in root):
  - Root handles URL fragments (#access_token=...) from Supabase redirects
  - Nested missing - password reset links won't work properly
  - **Impact:** Password reset flow broken

- **Auth debug accordion** (lines 175-217 in root):
  - Root has diagnostic UI for troubleshooting auth issues
  - Nested missing
  - **Impact:** Harder to debug production auth issues

- **Profile missing graceful handling** (lines 279-309 in root):
  - Root shows warning but doesn't logout when profile missing
  - Nested logs out immediately (lines 91-93)
  - **Impact:** Users with missing profiles can't access app at all

#### OPTIONAL (Instrumentation/Debug):
- **Auth instrumentation checkpoints** (lines 16-20, 384-385, 456-461 in root):
  - Root has extensive logging checkpoints
  - Nested missing
  - **Impact:** Less detailed logs, but not critical

---

### 2. `src/auth.py` (Root vs `auditops-streamlit/src/auth.py`)

#### MUST PORT (Security/Auth Correctness):
- **Structured login return value** (lines 10-197 in root):
  - Root returns `{"ok", "auth_ok", "profile_ok", "error", "user", "session", "profile"}`
  - Nested returns `dict | None` (lines 10-54)
  - **Impact:** UI can't distinguish auth failure vs profile missing

- **Explicit auth error handling** (lines 38-68 in root):
  - Root catches `sign_in_with_password` exceptions immediately
  - Nested catches all exceptions together
  - **Impact:** Wrong error messages shown to users

- **Session setting after login** (lines 89-124 in root):
  - Root explicitly sets session on client after `sign_in_with_password`
  - Nested missing - session may not be set correctly
  - **Impact:** Profile lookup may fail due to missing session

- **Profile lookup with `maybe_single()`** (lines 229-298 in root):
  - Root uses `.maybe_single()` to avoid exceptions when profile not found
  - Root uses `.eq("user_id", user_id)` (CORRECT)
  - Nested uses `.eq("id", user_id)` (WRONG - profiles table has `user_id`, not `id`)
  - **Impact:** Profile lookup always fails in production

- **Client parameter for profile lookup** (line 138, 229 in root):
  - Root accepts optional `client` parameter to reuse authenticated client
  - Nested always creates new client
  - **Impact:** Profile lookup may use unauthenticated client

- **reset_password function** (lines 557-615 in root):
  - Root has complete password reset implementation
  - Nested completely missing
  - **Impact:** Password reset page won't work

#### SHOULD PORT (Important UX):
- **Enhanced error logging** (lines 275-298 in root):
  - Root logs RLS/permission errors, error types, query strings
  - Nested minimal logging
  - **Impact:** Harder to diagnose production issues

- **Token authentication functions** (lines 360-554 in root):
  - Root has `authenticate_with_tokens`, `exchange_code_for_session`
  - Nested missing
  - **Impact:** Magic link/PKCE flows won't work (if used)

---

### 3. `src/config.py` (Root vs `auditops-streamlit/src/config.py`)

#### OPTIONAL (Documentation):
- **validate_config() comment** (lines 73-74 in root):
  - Root has comment: "NOTE: This only checks if secrets exist, NOT if they work."
  - Nested missing comment
  - **Impact:** Minor - documentation only

---

### 4. `src/supabase_client.py` (Root vs `auditops-streamlit/src/supabase_client.py`)

#### MUST PORT (Security/Auth Correctness):
- **Session rehydration in get_client()** (lines 47-104 in root):
  - Root rehydrates session from `st.session_state` on every `get_client()` call
  - Root checks if rehydration needed before doing it
  - Nested completely missing session rehydration
  - **Impact:** Sessions lost between Streamlit reruns, users logged out unexpectedly

- **Error handling in validate_config()** (lines 29-33 in root):
  - Root re-raises config errors (critical)
  - Nested just calls validate_config() without special handling
  - **Impact:** Config errors may be swallowed

#### OPTIONAL (Code Quality):
- **Import streamlit** (line 4 in root):
  - Root imports `streamlit as st` for session state access
  - Nested doesn't import streamlit
  - **Impact:** Required for rehydration logic

---

### 5. `src/db.py` (Root vs `auditops-streamlit/src/db.py`)

#### MUST PORT (Security/Auth Correctness):
- **Profile lookup uses `user_id`** (lines 18-36 in root):
  - Root: `.eq("user_id", user_id).single()`
  - Nested: `.eq("id", user_id)` (line 21) - **WRONG COLUMN**
  - **Impact:** Profile queries always fail - this is why "profile not found" errors occur

- **Schema-agnostic health check** (lines 86-98 in root):
  - Root: `.select("*").limit(1)` (schema-agnostic)
  - Nested: `.select("id").limit(1)` (line 69) - assumes `id` column exists
  - **Impact:** Health check fails if view doesn't have `id` column

- **Profile update uses `user_id`** (lines 58-76 in root):
  - Root: `.eq("user_id", user_id)`
  - Nested: `.eq("id", user_id)` (line 49) - **WRONG COLUMN**
  - **Impact:** Profile updates fail

---

### 6. `pages/00_Reset_Password.py`

✅ **IDENTICAL** - Both versions are the same. No changes needed.

---

### 7. `requirements.txt`

✅ **IDENTICAL** - Both versions are the same. No changes needed.

---

## Summary by Priority

### MUST PORT (Critical - Blocks Production):
1. `src/auth.py`: Structured login return, `user_id` column fix, `maybe_single()`, session handling, `reset_password()` function
2. `src/supabase_client.py`: Session rehydration logic
3. `src/db.py`: `user_id` column fixes (3 occurrences), schema-agnostic health check
4. `app.py`: Structured login result handling, session rehydration, fragment-to-query conversion

### SHOULD PORT (Important - UX Issues):
1. `app.py`: Profile missing graceful handling, auth debug accordion
2. `src/auth.py`: Enhanced error logging, token auth functions

### OPTIONAL (Nice to Have):
1. `app.py`: Auth instrumentation checkpoints
2. `src/config.py`: Documentation comment

---

## Files That Need Porting

**Critical (MUST PORT):**
- `auditops-streamlit/src/auth.py` - Complete rewrite needed
- `auditops-streamlit/src/supabase_client.py` - Add rehydration
- `auditops-streamlit/src/db.py` - Fix column names
- `auditops-streamlit/app.py` - Fix login handling, add session rehydration

**Important (SHOULD PORT):**
- `auditops-streamlit/app.py` - Add graceful profile handling, debug UI

**No Changes Needed:**
- `auditops-streamlit/pages/00_Reset_Password.py` ✅
- `auditops-streamlit/requirements.txt` ✅

---

## Next Steps

1. Port all MUST PORT changes to production files
2. Port SHOULD PORT changes for better UX
3. Archive root duplicate files to prevent confusion
4. Update documentation

