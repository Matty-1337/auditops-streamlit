# Deployment Alignment Report
**Generated:** 2025-12-25  
**Purpose:** Document Streamlit Cloud deployment structure and ensure code changes target the correct files

---

## Executive Summary

**CRITICAL FINDING:** Streamlit Cloud uses a **nested directory structure**. All production changes must be made in `auditops-streamlit/` directory, NOT the repository root.

---

## 1. Production Deployment Configuration

### Streamlit Cloud Settings
- **Repository:** `matty-1337/auditops-streamlit`
- **Branch:** `main`
- **Main Module (Entrypoint):** `auditops-streamlit/app.py` ⚠️
- **Requirements File:** `auditops-streamlit/requirements.txt` ⚠️
- **Working Directory:** `auditops-streamlit/` (implied by entrypoint path)

### Import Resolution
When Streamlit Cloud runs `auditops-streamlit/app.py`, Python resolves imports as follows:
- `from src.auth import ...` → Resolves to `auditops-streamlit/src/auth.py`
- `from src.config import ...` → Resolves to `auditops-streamlit/src/config.py`
- `pages/` directory → Resolves to `auditops-streamlit/pages/`

**✅ CONFIRMED:** Python import test shows nested `src/` directory is used when running from nested directory.

---

## 2. Repository Structure Audit

### Directory Tree (Key Paths Only)

```
auditops-streamlit/                    # Repository root
├── app.py                             # ⚠️ NOT USED BY PRODUCTION (21,655 bytes, 473 lines)
├── src/                               # ⚠️ NOT USED BY PRODUCTION
│   ├── auth.py
│   ├── config.py
│   ├── auth_debug.py                  # Extra files not in nested
│   ├── auth_instrumentation.py        # Extra files not in nested
│   └── ...
├── pages/                             # ⚠️ NOT USED BY PRODUCTION
│   ├── 00_Reset_Password.py
│   └── ...
├── requirements.txt                   # ⚠️ NOT USED BY PRODUCTION (has requests>=2.31.0)
└── auditops-streamlit/                # ✅ PRODUCTION DIRECTORY
    ├── app.py                         # ✅ PRODUCTION ENTRYPOINT (6,130 bytes, 171 lines)
    ├── src/                           # ✅ PRODUCTION SOURCE CODE
    │   ├── auth.py
    │   ├── config.py
    │   └── ... (no auth_debug.py, no auth_instrumentation.py)
    ├── pages/                         # ✅ PRODUCTION PAGES
    │   ├── 00_Reset_Password.py       # ✅ Recently copied
    │   └── ...
    └── requirements.txt               # ✅ PRODUCTION REQUIREMENTS (now includes requests)
```

---

## 3. Entrypoint Identification

### All Streamlit Entrypoints Found

| File Path | Purpose | Used in Production? | Notes |
|-----------|---------|---------------------|-------|
| `app.py` | Root entrypoint (advanced version) | ❌ NO | Contains instrumentation, fragment handling, advanced auth features. **NOT DEPLOYED.** |
| `auditops-streamlit/app.py` | Nested entrypoint (production) | ✅ **YES** | Simpler version. This is what Streamlit Cloud runs. |

### Key Differences Between Root and Nested app.py

| Feature | Root `app.py` | Nested `auditops-streamlit/app.py` |
|---------|---------------|------------------------------------|
| **Lines of code** | 473 lines | 171 lines |
| **File size** | 21,655 bytes | 6,130 bytes |
| **Build marker** | ❌ None | ✅ Has UTC timestamp marker |
| **Git SHA in marker** | ❌ No | ✅ Added in this audit |
| **Forgot password UI** | ✅ Yes | ✅ Yes |
| **JavaScript fragment handling** | ✅ Yes (complex) | ❌ No |
| **Auth instrumentation** | ✅ Yes | ❌ No |
| **Reset password page link** | ✅ Yes | ✅ Yes |

---

## 4. Duplication & Drift Detection

### Files with Duplicates

#### 4.1 `app.py` (Root vs Nested)
- **Root:** Advanced version with instrumentation, fragment conversion, complex auth flow
- **Nested:** Simplified version, production-ready but missing some features
- **Drift:** Most recent auth/login changes (commits `eb19d8a`, `84c1b13`, `9c95c8d`, `67d4627`, etc.) were applied to **root** `app.py` but **NOT** to nested
- **Impact:** ⚠️ **HIGH** - Production is missing many recent fixes

#### 4.2 `src/auth.py` (Root vs Nested)
- **Root:** Has `auth_debug.py`, `auth_instrumentation.py` dependencies
- **Nested:** Simpler version, no instrumentation dependencies
- **Drift:** Likely differences in error handling, structured login results
- **Impact:** ⚠️ **MEDIUM** - May affect error messages and user experience

#### 4.3 `pages/00_Reset_Password.py`
- **Root:** Original version (421 lines)
- **Nested:** ✅ Recently copied (commit `48d0a56`)
- **Status:** ✅ **ALIGNED** - Both should be identical now

#### 4.4 `requirements.txt`
- **Root:** Contains `requests>=2.31.0`
- **Nested:** ❌ Was missing `requests>=2.31.0` (now fixed)
- **Impact:** ⚠️ **MEDIUM** - Admin tools and some features may fail
- **Status:** ✅ **FIXED** - Added `requests>=2.31.0` to nested requirements.txt

---

## 5. Git History Analysis

### Recent Commits Affecting Auth/Login/Reset Password

| Commit | Files Changed | Applied to Production? |
|--------|---------------|------------------------|
| `48d0a56` | `auditops-streamlit/app.py`, `auditops-streamlit/pages/00_Reset_Password.py` | ✅ **YES** |
| `eb19d8a` | `app.py` (root) | ❌ **NO** - Wrong file |
| `84c1b13` | `app.py` (root) | ❌ **NO** - Wrong file |
| `9c95c8d` | `app.py` (root) | ❌ **NO** - Wrong file |
| `67d4627` | `app.py` (root), `pages/00_Reset_Password.py` (root) | ❌ **NO** - Wrong file |
| `0d99b71` | `app.py` (root), `src/auth.py` (root) | ❌ **NO** - Wrong file |
| `e17b008` | `src/auth.py` (root) | ❌ **NO** - Wrong file |

**Finding:** Only commit `48d0a56` actually modified the production entrypoint. All other recent changes were applied to the **wrong** `app.py` file.

---

## 6. Canonical Runtime Path Confirmation

### Production Entrypoint
```
auditops-streamlit/app.py
```

### Canonical Directories (Used by Production)

| Directory | Production Path | Purpose |
|-----------|-----------------|---------|
| **Source code** | `auditops-streamlit/src/` | All Python modules (`auth.py`, `config.py`, `db.py`, etc.) |
| **Pages** | `auditops-streamlit/pages/` | All Streamlit pages (`00_Reset_Password.py`, etc.) |
| **Requirements** | `auditops-streamlit/requirements.txt` | Python dependencies |
| **SQL schemas** | `auditops-streamlit/sql/` | Database schema files |

### Import Resolution Map

When `auditops-streamlit/app.py` imports:
- `from src.auth import login` → `auditops-streamlit/src/auth.py`
- `from src.config import ROLE_ADMIN` → `auditops-streamlit/src/config.py`
- `from src.supabase_client import get_client` → `auditops-streamlit/src/supabase_client.py`

Streamlit automatically looks for `pages/` in the same directory as the entrypoint:
- `pages/00_Reset_Password.py` → `auditops-streamlit/pages/00_Reset_Password.py`

---

## 7. Files Previously Edited But Not Used by Production

The following files were modified in recent commits but are **NOT** used by Streamlit Cloud production:

1. **`app.py` (root)** - All recent changes to this file were ignored by production
2. **`src/auth.py` (root)** - Changes to structured login results, error handling
3. **`pages/00_Reset_Password.py` (root)** - Original implementation (now copied to nested)
4. **`src/db.py` (root)** - Health check fixes
5. **`src/auth_debug.py`** - Debug utilities (not in nested directory)
6. **`src/auth_instrumentation.py`** - Instrumentation code (not in nested directory)

**Recommendation:** Future changes should **ONLY** be made in `auditops-streamlit/` directory. The root files may be kept for local development or removed to prevent confusion.

---

## 8. Build Marker Implementation

### Production Build Marker (auditops-streamlit/app.py)

Added permanent build marker that displays:
- **Git SHA** (short, 7 characters)
- **Build timestamp** (UTC)
- **Entrypoint path** (explicit file path)

**Location:** Lines 41-53 in `auditops-streamlit/app.py`

**Display format:**
```
🔧 BUILD: <sha> | <timestamp> UTC | ENTRYPOINT: auditops-streamlit/app.py
```

**Purpose:**
- Verify that Streamlit Cloud has deployed the latest commit
- Confirm the correct entrypoint file is running
- Debug deployment issues quickly

---

## 9. Requirements.txt Alignment

### Production Requirements (auditops-streamlit/requirements.txt)

**Before fix:**
```
streamlit>=1.28.0
supabase>=2.0.0
pandas>=2.0.0
reportlab>=4.0.0
```

**After fix:**
```
streamlit>=1.28.0
supabase>=2.0.0
pandas>=2.0.0
reportlab>=4.0.0
requests>=2.31.0
```

**Change:** Added `requests>=2.31.0` (required for admin tools and some auth features).

**Status:** ✅ **FIXED**

---

## 10. Forgot Password & Reset Flow Verification

### Production Entrypoint (auditops-streamlit/app.py)

✅ **Forgot Password UI:** Implemented (lines 66-69, function at lines 104-142)
- Button appears below login form
- `show_forgot_password()` function calls `client.auth.reset_password_for_email()`
- Generic success message (prevents email enumeration)

✅ **Reset Password Page:** Exists at `auditops-streamlit/pages/00_Reset_Password.py`
- Handles recovery tokens from email links
- Shows password reset form
- Updates password via `client.auth.update_user()`

✅ **Status:** Both features are present in production files.

---

## 11. Where Future Edits Must Be Made

### ✅ CORRECT: Edit These Files for Production

All changes for Streamlit Cloud production must be made in the **`auditops-streamlit/`** directory:

| File Type | Production Path | Notes |
|-----------|-----------------|-------|
| **Main app** | `auditops-streamlit/app.py` | Entrypoint - ALWAYS edit this one |
| **Auth logic** | `auditops-streamlit/src/auth.py` | Authentication functions |
| **Config** | `auditops-streamlit/src/config.py` | Configuration and secrets |
| **Database** | `auditops-streamlit/src/db.py` | Database operations |
| **Pages** | `auditops-streamlit/pages/*.py` | All Streamlit pages |
| **Requirements** | `auditops-streamlit/requirements.txt` | Python dependencies |
| **SQL schemas** | `auditops-streamlit/sql/*.sql` | Database schemas |

### ❌ WRONG: Do NOT Edit These Files for Production

These files are **NOT** used by Streamlit Cloud:

| File Path | Status | Action |
|-----------|--------|--------|
| `app.py` (root) | ❌ Ignored by production | Keep for local dev or remove |
| `src/` (root) | ❌ Ignored by production | Keep for local dev or remove |
| `pages/` (root) | ❌ Ignored by production | Keep for local dev or remove |
| `requirements.txt` (root) | ❌ Ignored by production | Keep for local dev or remove |

---

## 12. Remediation Actions Taken

1. ✅ **Added permanent build marker** to `auditops-streamlit/app.py` with Git SHA
2. ✅ **Fixed requirements.txt** - Added `requests>=2.31.0` to `auditops-streamlit/requirements.txt`
3. ✅ **Verified Forgot Password UI** - Confirmed it exists in production entrypoint
4. ✅ **Verified Reset Password page** - Confirmed it exists in `auditops-streamlit/pages/`
5. ✅ **Created this report** - Documented deployment structure

---

## 13. Verification Steps

### Step 1: Verify Build Marker in Production

1. Open Streamlit Cloud app: `https://auditops.streamlit.app`
2. Navigate to login page
3. Look for build marker at top of page:
   ```
   🔧 BUILD: <sha> | <timestamp> UTC | ENTRYPOINT: auditops-streamlit/app.py
   ```
4. Verify SHA matches latest commit: `git rev-parse --short HEAD`

### Step 2: Verify Forgot Password Button

1. On login page, look for "Forgot password?" button below login form
2. Click button - should show email input form
3. Enter email and click "Send Reset Link"
4. Should see: "✅ If the email exists, you'll receive a reset link."

### Step 3: Verify Reset Password Page

1. Request password reset via "Forgot password?" button
2. Click reset link in email
3. Should redirect to Reset Password page (accessible via sidebar as "00_Reset_Password")
4. Should show password reset form

### Step 4: Verify Requirements.txt

1. Check Streamlit Cloud logs for dependency installation
2. Verify `requests` package is installed (no import errors)
3. Admin tools should work if using requests

---

## 14. Recommendations

### Immediate Actions

1. ✅ **Use this report** as reference for all future changes
2. ✅ **Always edit files in `auditops-streamlit/`** directory
3. ✅ **Check build marker** after each deployment to confirm latest code is running

### Optional Cleanup (Future)

1. Consider removing or archiving root `app.py`, `src/`, `pages/` to prevent confusion
2. Add a README in root explaining the nested structure
3. Add pre-commit hook or CI check to warn if editing root files

### Documentation Updates Needed

1. Update README.md to clarify nested structure
2. Add deployment guide explaining which files to edit
3. Document the build marker verification process

---

## 15. Commit Information

**Commit Hash:** `48d0a56` (previous) → `<new_hash>` (after fixes)  
**Files Changed:**
- `auditops-streamlit/app.py` - Added permanent build marker with Git SHA
- `auditops-streamlit/requirements.txt` - Added `requests>=2.31.0`
- `DEPLOYMENT_ALIGNMENT_REPORT.md` - This report

---

## Conclusion

✅ **Production entrypoint confirmed:** `auditops-streamlit/app.py`  
✅ **Canonical directories documented:** All production code in `auditops-streamlit/`  
✅ **Build marker added:** Visible verification of deployment  
✅ **Requirements fixed:** Missing `requests` package added  
✅ **Password reset flow verified:** Both Forgot Password UI and Reset Password page exist  

**All future changes must target files in `auditops-streamlit/` directory.**

