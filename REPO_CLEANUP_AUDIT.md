# REPOSITORY CLEANUP AUDIT REPORT
**Project:** matty-1337/auditops-streamlit
**Date:** 2025-12-25
**Auditor:** Claude Code
**Status:** REPORT ONLY - NO DELETIONS PERFORMED

---

## A) Executive Summary

### What's Clean
✅ **Production runtime path is well-defined**: `auditops-streamlit/app.py` is the confirmed Streamlit Cloud entrypoint
✅ **Archive is clearly documented**: `archive_root_app/` has a README explaining it's not used in production
✅ **All production modules are actively used** (except storage.py - see below)
✅ **No dangerous import collisions** in the production runtime path

### What's Confusing
❌ **Complete duplicate codebase** in `archive_root_app/` with ALL files (app.py, src/, pages/)
❌ **Broken test files** at repo root that import non-existent modules (`src.auth_debug`)
❌ **SQL schema duplicates** - 3 different schema files in 3 different locations
❌ **Unused production module**: `auditops-streamlit/src/storage.py` (147 lines) has ZERO imports
❌ **16 documentation markdown files** at repo root (4,026 total lines) - many appear to be historical reports

### Highest Risk Issues

**RISK #1: Import Path Ambiguity**
- **Issue**: Python could import from `archive_root_app/src/` instead of `auditops-streamlit/src/` if PYTHONPATH is misconfigured
- **Severity**: MEDIUM (Streamlit Cloud should use working directory correctly, but local dev could be affected)
- **Evidence**: Both directories contain identically-named modules (`auth.py`, `db.py`, etc.)

**RISK #2: Broken Test Files**
- **Issue**: `test_auth_flow.py` and `test_auth_system.py` import `src.auth_debug` which doesn't exist in production
- **Severity**: LOW (tests are not in runtime path, but developers might waste time trying to run them)
- **Evidence**: Lines 5 and 7 import from non-existent `src.auth_debug` module

**RISK #3: SQL Schema Confusion**
- **Issue**: Three different `schema.sql` files exist, all different from each other
- **Severity**: MEDIUM (unclear which is source of truth for database schema)
- **Locations**: `/sql/schema.sql`, `/auditops-streamlit/sql/schema.sql`, migration files

---

## B) Production Runtime Map

### Confirmed Streamlit Entrypoint
**Primary Entrypoint:** `auditops-streamlit/app.py` (30,099 bytes, 389 lines)

### Production File Set (Used at Runtime)

#### Core Application
- ✅ `auditops-streamlit/app.py` - Main entrypoint
- ✅ `auditops-streamlit/requirements.txt` - Dependencies (6 packages)

#### Source Modules (`auditops-streamlit/src/`)
- ✅ `__init__.py` (38 bytes) - Package marker
- ✅ `auth.py` (693 lines) - **HEAVILY USED** - Authentication, login, logout, password reset
- ✅ `config.py` (179 lines) - **HEAVILY USED** - Role constants, config validation
- ✅ `db.py` (419 lines) - **HEAVILY USED** - Database operations (shifts, clients, pay periods)
- ✅ `pdf_statements.py` (246 lines) - **USED** - PDF generation (2 imports from pages)
- ✅ `supabase_client.py` (170 lines) - **HEAVILY USED** - Client initialization, session persistence
- ✅ `utils.py` (170 lines) - **HEAVILY USED** - Formatting helpers (date, currency, duration)
- ❌ `storage.py` (147 lines) - **UNUSED** - Zero imports, dead code

#### Pages (`auditops-streamlit/pages/`)
All 8 page files are active in production:
- ✅ `00_Reset_Password.py` - Password reset flow
- ✅ `01_Auditor_Field_Mode.py` - Field auditor shift entry
- ✅ `02_Auditor_My_Pay.py` - Auditor pay statements
- ✅ `10_Admin_Approvals.py` - Shift approval workflow
- ✅ `11_Admin_Pay_Periods.py` - Pay period management
- ✅ `12_Admin_Clients.py` - Client management
- ✅ `13_Admin_Secrets_Access_Log.py` - Access logging
- ✅ `99_Admin_Health_Check.py` - System diagnostics

### Streamlit Configuration
- ✅ `.streamlit/config.toml` (1 line, minimal)
- ✅ `.streamlit/secrets.toml.example` (example secrets file)

**Deployment Note:** Streamlit Cloud reads secrets from its own dashboard, not from `.streamlit/secrets.toml`

### Import Analysis

**All production modules imported:**
```
auth.py          → Imported by: app.py, all pages (login, logout, require_authentication)
config.py        → Imported by: app.py, all pages (ROLE_*, status constants)
db.py            → Imported by: 6 pages (get_shifts, get_clients, get_pay_periods, etc.)
pdf_statements.py→ Imported by: 2 pages (generate_pay_statement_pdf, generate_pay_period_summary_pdf)
supabase_client.py→ Imported by: app.py, auth.py (get_client, persist_session)
utils.py         → Imported by: 6 pages (format_date, format_currency, format_duration, etc.)

storage.py       → ❌ ZERO IMPORTS (unused dead code)
```

---

## C) Duplicate & Collision Findings

| Path A | Path B | Why Duplicate | Risk | Recommendation |
|--------|--------|---------------|------|----------------|
| `auditops-streamlit/app.py` | `archive_root_app/app.py` | Complete archive of old version | LOW (archive documented) | **DELETE** archive |
| `auditops-streamlit/src/*.py` (8 files) | `archive_root_app/src/*.py` (10 files) | Complete archive of old modules | MEDIUM (import ambiguity) | **DELETE** archive |
| `auditops-streamlit/pages/*.py` (8 files) | `archive_root_app/pages/*.py` (8 files) | Complete archive of old pages | LOW (Streamlit uses working dir) | **DELETE** archive |
| `auditops-streamlit/sql/schema.sql` | `/sql/schema.sql` | Root-level duplicate schema | MEDIUM (schema confusion) | **DELETE** root duplicate |
| `auditops-streamlit/supabase_migration.sql.txt` | `/supabase_migration.sql.txt` | Root-level migration duplicate | LOW (reference file) | **DELETE** root duplicate |
| `auditops-streamlit/requirements.txt` | `archive_root_app/requirements.txt` | Archive duplicate | LOW (archive documented) | **DELETE** with archive |

### Archive-Only Files (Not in Production)
These files exist ONLY in `archive_root_app/src/` and were never ported to production:
- `auth_debug.py` (6,753 bytes) - Debug utilities for auth flow
- `auth_instrumentation.py` (8,882 bytes) - Auth instrumentation

**Status:** Safe to delete with entire archive (not used anywhere)

---

## D) Full File Inventory

### Production Files (`auditops-streamlit/`)

| Path | Type | Runtime? | Evidence | Status | Notes |
|------|------|----------|----------|--------|-------|
| `app.py` | Python | **YES** | Streamlit entrypoint | **KEEP** | Main app (389 lines) |
| `requirements.txt` | Config | **YES** | Deployed to Streamlit Cloud | **KEEP** | 6 dependencies |
| `README.md` | Docs | NO | Local documentation | KEEP | Project docs |
| `supabase_migration.sql.txt` | SQL | NO | Reference only | DELETE CANDIDATE | Duplicate of `/supabase_migration.sql.txt` |
| `src/__init__.py` | Python | YES | Package marker | **KEEP** | Required for imports |
| `src/auth.py` | Python | **YES** | Imported by app.py + all pages | **KEEP** | Core auth (693 lines) |
| `src/config.py` | Python | **YES** | Imported by app.py + all pages | **KEEP** | Config + constants (179 lines) |
| `src/db.py` | Python | **YES** | Imported by 6 pages | **KEEP** | Database ops (419 lines) |
| `src/pdf_statements.py` | Python | **YES** | Imported by pages 02, 11 | **KEEP** | PDF generation (246 lines) |
| `src/storage.py` | Python | **NO** | Zero imports found | **DELETE CANDIDATE** | Unused dead code (147 lines) |
| `src/supabase_client.py` | Python | **YES** | Imported by app.py, auth.py | **KEEP** | Client init (170 lines) |
| `src/utils.py` | Python | **YES** | Imported by 6 pages | **KEEP** | Formatting helpers (170 lines) |
| `sql/schema.sql` | SQL | NO | Reference/migration | **KEEP** | Production schema source |
| `pages/00_Reset_Password.py` | Python | **YES** | Streamlit page | **KEEP** | Password reset |
| `pages/01_Auditor_Field_Mode.py` | Python | **YES** | Streamlit page | **KEEP** | Shift entry |
| `pages/02_Auditor_My_Pay.py` | Python | **YES** | Streamlit page | **KEEP** | Pay statements |
| `pages/10_Admin_Approvals.py` | Python | **YES** | Streamlit page | **KEEP** | Approvals |
| `pages/11_Admin_Pay_Periods.py` | Python | **YES** | Streamlit page | **KEEP** | Pay periods |
| `pages/12_Admin_Clients.py` | Python | **YES** | Streamlit page | **KEEP** | Client management |
| `pages/13_Admin_Secrets_Access_Log.py` | Python | **YES** | Streamlit page | **KEEP** | Access logs |
| `pages/99_Admin_Health_Check.py` | Python | **YES** | Streamlit page | **KEEP** | Health check |

### Archive (`archive_root_app/`)

| Path | Type | Runtime? | Evidence | Status | Notes |
|------|------|----------|----------|--------|-------|
| `archive_root_app/README.md` | Docs | NO | Archive documentation | DELETE CANDIDATE | Explains archive purpose |
| `archive_root_app/app.py` | Python | NO | Differs from production | **DELETE CANDIDATE** | Old version |
| `archive_root_app/requirements.txt` | Config | NO | Old dependencies | DELETE CANDIDATE | Not deployed |
| `archive_root_app/src/*.py` (10 files) | Python | NO | All differ from production | **DELETE CANDIDATE** | Old source code |
| `archive_root_app/pages/*.py` (8 files) | Python | NO | All differ from production | **DELETE CANDIDATE** | Old pages |

**Total archive size:** ~40 files, complete duplicate codebase

### Root-Level Files

| Path | Type | Runtime? | Evidence | Status | Notes |
|------|------|----------|----------|--------|-------|
| `.gitignore` | Config | NO | Git configuration | **KEEP** | Standard |
| `.streamlit/config.toml` | Config | **YES** | Streamlit runtime config | **KEEP** | Minimal (1 line) |
| `.streamlit/secrets.toml.example` | Docs | NO | Example secrets | KEEP | Reference |
| `DEPLOYMENT_STATUS.md` | Docs | NO | Deployment notes (recent) | KEEP | Current work artifact |
| `README.md` | Docs | NO | Main project README | **KEEP** | Primary docs |
| `AUTHENTICATION_FIX_REPORT.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `AUTHENTICATION_FIX_SUMMARY.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `AUTH_FLOW_MAP.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `AUTH_INVESTIGATION_REPORT.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `DEPLOYMENT_ALIGNMENT_REPORT.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `DRIFT_SYNC_REPORT.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `FINAL_VERDICT.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `PASSWORD_AUTH_IMPLEMENTATION.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `PASSWORD_RESET_IMPLEMENTATION.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `README_AUTH_FIX.md` | Docs | NO | Historical README | DELETE CANDIDATE | Superseded |
| `README_PASSWORD_AUTH.md` | Docs | NO | Historical README | DELETE CANDIDATE | Superseded |
| `README_PASSWORD_RESET.md` | Docs | NO | Historical README | DELETE CANDIDATE | Superseded |
| `ROOT_CAUSE.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `SYNC_COMPLETE.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `SYSTEM_TEST_REPORT.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `UX_RACE_FIX_SUMMARY.md` | Docs | NO | Historical report | DELETE CANDIDATE | Old investigation |
| `test_auth_flow.py` | Python | NO | Imports non-existent `src.auth_debug` | **DELETE CANDIDATE** | Broken test |
| `test_auth_system.py` | Python | NO | Imports non-existent `src.auth_debug` | **DELETE CANDIDATE** | Broken test |
| `sql/schema.sql` | SQL | NO | Differs from production | DELETE CANDIDATE | Use production version |
| `supabase_migration.sql.txt` | SQL | NO | Differs from production | DELETE CANDIDATE | Use production version |
| `tools/admin_set_password.py` | Python | NO | Standalone admin tool | KEEP | Useful utility |

**Total root-level cruft:** 16 historical markdown files (4,026 lines), 2 broken tests, 2 duplicate SQL files

---

## E) Recommended Deletion Plan

### High Confidence - Safe to Delete

**Category: Complete Archive Duplication**
```bash
archive_root_app/               # Entire directory (40+ files)
├── app.py                       # Old version of production app
├── pages/*.py                   # Old versions of production pages (8 files)
├── src/*.py                     # Old versions of production modules (10 files)
├── requirements.txt             # Old dependencies
└── README.md                    # Archive documentation
```
**Rationale:** README confirms these are archived duplicates not used in production. All critical fixes have been ported to `auditops-streamlit/`.

**Category: Unused Production Module**
```bash
auditops-streamlit/src/storage.py
```
**Rationale:** Zero imports found in entire codebase. 147 lines of dead code. Only reference is in `99_Admin_Health_Check.py` testing if storage API exists (not importing the module).

**Category: Broken Test Files**
```bash
test_auth_flow.py               # Imports src.auth_debug (doesn't exist)
test_auth_system.py             # Imports src.auth_debug (doesn't exist)
```
**Rationale:** Both import `src.auth_debug` which only exists in archive. Tests cannot run without errors.

**Category: Duplicate SQL Files**
```bash
sql/schema.sql                  # Root duplicate
supabase_migration.sql.txt      # Root duplicate
auditops-streamlit/supabase_migration.sql.txt  # Production duplicate
```
**Rationale:** Keep `auditops-streamlit/sql/schema.sql` as single source of truth. Root duplicates differ and cause confusion.

**Category: Historical Documentation (12 files)**
```bash
AUTHENTICATION_FIX_REPORT.md
AUTHENTICATION_FIX_SUMMARY.md
AUTH_FLOW_MAP.md
AUTH_INVESTIGATION_REPORT.md
DEPLOYMENT_ALIGNMENT_REPORT.md
DRIFT_SYNC_REPORT.md
FINAL_VERDICT.md
PASSWORD_AUTH_IMPLEMENTATION.md
PASSWORD_RESET_IMPLEMENTATION.md
ROOT_CAUSE.md
SYNC_COMPLETE.md
SYSTEM_TEST_REPORT.md
UX_RACE_FIX_SUMMARY.md
README_AUTH_FIX.md
README_PASSWORD_AUTH.md
README_PASSWORD_RESET.md
```
**Rationale:** Historical investigation reports (4,026 lines total). Useful context but not needed for production. Can be archived in git history.

**Total Impact:** ~60 files, ~8,000 lines of code/docs

### Medium Confidence - Review Recommended

**Category: Tools Directory**
```bash
tools/admin_set_password.py     # KEEP - useful admin utility
```
**Rationale:** Standalone utility for creating/updating user passwords via Supabase Admin API. Not in runtime path but useful for ops.

**Category: Current Work Artifacts**
```bash
DEPLOYMENT_STATUS.md            # KEEP - created recently (Dec 25)
```
**Rationale:** Recent file documenting current deployment status. May still be relevant.

**Category: Primary Documentation**
```bash
README.md                       # KEEP - main project docs
auditops-streamlit/README.md    # KEEP - production docs
.streamlit/secrets.toml.example # KEEP - helpful reference
```

### Do Not Delete

**Production Runtime Files:**
- Entire `auditops-streamlit/` directory (except `storage.py` and `supabase_migration.sql.txt`)
- `.streamlit/config.toml`
- `.gitignore`
- `tools/admin_set_password.py`

---

## F) "Before Deleting" Checklist

### Step 1: Verify Production Runtime
```bash
# Confirm Streamlit Cloud deployment settings
# Branch: main (or current deployment branch)
# App file: auditops-streamlit/app.py
```

### Step 2: Search for Hidden Dependencies
```bash
# Search for any imports of storage module
cd /home/user/auditops-streamlit
grep -r "from src.storage import\|import src.storage" auditops-streamlit/ --include="*.py"
# Result: Should be empty (confirmed zero imports)

# Search for references to archive files
grep -r "archive_root_app" . --include="*.py" --include="*.md"
# Result: Should only be in archive README and this audit report

# Search for auth_debug imports
grep -r "auth_debug\|auth_instrumentation" . --include="*.py"
# Result: Should only be in test_auth_flow.py and test_auth_system.py
```

### Step 3: Verify Imports Still Work
```bash
# Start Python in production directory
cd auditops-streamlit
python3 -c "
from src.auth import login, logout, is_authenticated
from src.config import ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR
from src.db import get_all_clients
from src.supabase_client import get_client
from src.utils import format_date
from src.pdf_statements import generate_pay_statement_pdf
print('✅ All production imports successful')
"
```

### Step 4: Test Locally (if possible)
```bash
cd auditops-streamlit
streamlit run app.py
# Verify app loads without import errors
# Test login flow
# Test at least one page navigation
```

### Step 5: Create Safety Backup
```bash
# Create git branch with current state before deletion
git checkout -b backup-before-cleanup
git add -A
git commit -m "Backup before repository cleanup"
git push -u origin backup-before-cleanup

# OR create tarball backup
tar -czf backup-$(date +%Y%m%d).tar.gz \
  archive_root_app/ \
  test_auth_*.py \
  sql/ \
  *.md
```

### Step 6: Perform Deletions (After Approval)
```bash
# HIGH CONFIDENCE DELETIONS
rm -rf archive_root_app/
rm test_auth_flow.py
rm test_auth_system.py
rm auditops-streamlit/src/storage.py
rm -rf sql/
rm supabase_migration.sql.txt
rm auditops-streamlit/supabase_migration.sql.txt

# HISTORICAL DOCS DELETIONS
rm AUTHENTICATION_FIX_REPORT.md
rm AUTHENTICATION_FIX_SUMMARY.md
rm AUTH_FLOW_MAP.md
rm AUTH_INVESTIGATION_REPORT.md
rm DEPLOYMENT_ALIGNMENT_REPORT.md
rm DRIFT_SYNC_REPORT.md
rm FINAL_VERDICT.md
rm PASSWORD_AUTH_IMPLEMENTATION.md
rm PASSWORD_RESET_IMPLEMENTATION.md
rm ROOT_CAUSE.md
rm SYNC_COMPLETE.md
rm SYSTEM_TEST_REPORT.md
rm UX_RACE_FIX_SUMMARY.md
rm README_AUTH_FIX.md
rm README_PASSWORD_AUTH.md
rm README_PASSWORD_RESET.md
```

### Step 7: Verify Clean State
```bash
# Verify no broken imports
cd auditops-streamlit
python3 -c "import app; print('✅ app.py imports successfully')"

# Check git status
git status
# Should show deleted files

# Test streamlit locally (if possible)
streamlit run app.py
```

### Step 8: Commit Cleanup
```bash
git add -A
git commit -m "chore: remove archive, unused modules, and historical docs

- Delete archive_root_app/ (complete old codebase duplicate)
- Delete unused src/storage.py (zero imports)
- Delete broken test files (import non-existent modules)
- Delete duplicate SQL files (keep production version only)
- Delete 16 historical markdown investigation reports
- Keep tools/admin_set_password.py (useful utility)
- Keep DEPLOYMENT_STATUS.md (current work)
- Keep primary README files

See REPO_CLEANUP_AUDIT.md for full analysis."

git push
```

### Step 9: Deploy and Verify
```bash
# Verify Streamlit Cloud deployment succeeds
# Check app loads in production
# Test authentication flow
# Test key user workflows
```

### Step 10: Monitor for Issues
```bash
# After deployment, monitor for:
# - Import errors in logs
# - Module not found errors
# - Broken page loads
# - Missing functionality

# If issues found:
git revert HEAD  # Revert cleanup commit
# OR restore from backup branch
```

---

## Summary Statistics

### Files to Delete (High Confidence)
- Archive directory: **40 files** (~1,500 lines of code)
- Unused module: **1 file** (147 lines)
- Broken tests: **2 files** (305 lines)
- Duplicate SQL: **3 files** (~30 KB)
- Historical docs: **16 files** (4,026 lines)
- **Total: 62 files, ~6,000 lines**

### Files to Keep
- Production runtime: **26 files** (auditops-streamlit/)
- Config files: **3 files** (.gitignore, .streamlit/)
- Tools: **1 file** (admin_set_password.py)
- Current docs: **2 files** (README.md, DEPLOYMENT_STATUS.md)
- **Total: 32 files**

### Impact Analysis
- **Repository size reduction:** ~70% fewer files
- **Code duplication:** Eliminated 100%
- **Import ambiguity risk:** Eliminated
- **Schema confusion:** Eliminated (single source of truth)
- **Maintenance burden:** Significantly reduced

---

## Appendix: Import Graph

### Production Import Dependencies
```
app.py
├─→ src.auth (login, logout, is_authenticated, get_current_profile, require_authentication)
├─→ src.config (ROLE_ADMIN, ROLE_MANAGER, ROLE_AUDITOR)
└─→ src.supabase_client (get_client)

pages/00_Reset_Password.py
├─→ src.auth (establish_recovery_session, update_password)
└─→ src.config (require_role_access, ROLE_ADMIN, validate_config, get_supabase_url, get_supabase_key)

pages/01_Auditor_Field_Mode.py
├─→ src.auth (require_authentication, get_current_user, get_current_profile)
├─→ src.config (require_role_access, ROLE_AUDITOR, SHIFT_STATUS_*)
├─→ src.db (get_shifts, create_shift, update_shift, delete_shift, get_all_clients)
└─→ src.utils (format_datetime, format_duration, calculate_hours, render_status_badge, get_client_display_name)

pages/02_Auditor_My_Pay.py
├─→ src.auth (require_authentication, get_current_user)
├─→ src.config (require_role_access, ROLE_AUDITOR)
├─→ src.db (get_pay_items_by_auditor, get_all_pay_periods)
├─→ src.pdf_statements (generate_pay_statement_pdf) ⚠️
└─→ src.utils (format_date, format_currency, format_duration)

pages/10_Admin_Approvals.py
├─→ src.auth (require_authentication, get_current_user, get_current_profile)
├─→ src.config (require_role_access, ROLE_MANAGER, ROLE_ADMIN, SHIFT_STATUS_*)
├─→ src.db (get_submitted_shifts, get_shift, create_approval, get_approvals_by_shift)
└─→ src.utils (format_datetime, get_user_display_name, get_client_display_name)

pages/11_Admin_Pay_Periods.py
├─→ src.auth (require_authentication)
├─→ src.config (require_role_access, ROLE_ADMIN, PAY_PERIOD_*)
├─→ src.db (get_all_pay_periods, create_pay_period, update_pay_period, get_pay_items_for_period, ...)
├─→ src.pdf_statements (generate_pay_period_summary_pdf) ⚠️
└─→ src.utils (format_date, format_currency)

pages/12_Admin_Clients.py
├─→ src.auth (require_authentication, get_current_user)
├─→ src.config (require_role_access, ROLE_ADMIN)
├─→ src.db (get_all_clients, create_client, update_client, delete_client, get_client_by_id)
└─→ src.supabase_client (get_client)

pages/13_Admin_Secrets_Access_Log.py
├─→ src.auth (require_authentication, get_current_user)
├─→ src.config (require_role_access, ROLE_ADMIN)
├─→ src.db (get_access_logs, get_all_clients)
└─→ src.utils (format_datetime)

pages/99_Admin_Health_Check.py
├─→ src.auth (require_authentication)
├─→ src.config (require_role_access, ROLE_ADMIN)
├─→ src.supabase_client (get_client, reset_clients)
└─→ src.db (create_access_log)
```

### Orphaned Modules (No Imports)
```
src.storage
└─→ ❌ ZERO IMPORTS (dead code)
```

---

**END OF AUDIT REPORT**
