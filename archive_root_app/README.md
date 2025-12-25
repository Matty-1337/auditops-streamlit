# Archive: Root App Files (NOT USED IN PRODUCTION)

## ⚠️ IMPORTANT: DO NOT EDIT THESE FILES

These files are **archived duplicates** of the root-level app structure. They are **NOT used by Streamlit Cloud production deployment**.

## Why These Files Exist

During development, changes were accidentally applied to root-level files (`app.py`, `src/`, `pages/`, `requirements.txt`) instead of the production files in `auditops-streamlit/`.

**Streamlit Cloud runs from:** `auditops-streamlit/app.py`  
**These files are:** Historical copies kept for reference only

## Production Files Location

All production code lives in:
- `auditops-streamlit/app.py` - Main entrypoint
- `auditops-streamlit/src/` - Source code
- `auditops-streamlit/pages/` - Streamlit pages
- `auditops-streamlit/requirements.txt` - Dependencies

## What Was Ported

Critical fixes from these root files have been ported to production:
- Structured login result handling
- Session rehydration logic
- Profile lookup using `user_id` (not `id`)
- Password reset functionality
- JavaScript fragment-to-query conversion

See `DRIFT_SYNC_REPORT.md` for complete details.

## Action Required

**DO NOT:**
- Edit files in this archive
- Use these files for development
- Reference these files in documentation

**DO:**
- Edit files in `auditops-streamlit/` for all changes
- Reference `DEPLOYMENT_ALIGNMENT_REPORT.md` for canonical paths
- Delete this archive if you're confident all fixes are ported

