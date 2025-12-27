# PostgREST APIError Diagnostic & Fix Guide

This guide documents the comprehensive diagnostic and preventive measures implemented to resolve and prevent PostgREST APIErrors in the Admin Approvals page.

## 🐛 Problem Summary

**Original Error:**
```
postgrest.exceptions.APIError: This app has encountered an error.
The original error message is redacted to prevent data leaks.
```

**Location:** `/pages/10_Admin_Approvals.py` line 93, calling `get_approvals_by_shift()`

**Root Cause:** The query used a broken foreign key join `approver:profiles(*)` that failed because:
1. The `approver_id` field contains `auth_uuid` values that should reference `app_users` table
2. The foreign key relationship to `profiles` table was broken or misconfigured
3. The app has migrated from `profiles` to `app_users` table

## ✅ Solution Implemented

The approval functions now:
- **Avoid broken foreign key joins** by fetching data without joins
- **Manually fetch approver data** from `app_users` table using `auth_uuid`
- **Use service_role=True** to bypass RLS policies
- **Validate inputs** and handle errors gracefully
- **Return empty lists** instead of crashing when errors occur

## 📋 Changes Made

### 1. Enhanced Error Logging (`src/db.py`)

Added two decorators for comprehensive error tracking:

- **`@log_postgrest_errors`**: Captures full APIError details before Streamlit redacts them
  - Logs to console and `/tmp/postgrest_errors.log`
  - Extracts error codes, messages, hints, and details

- **`@track_api_errors`**: Monitors API errors for alerting
  - Ready for integration with Sentry, CloudWatch, etc.
  - Logs structured data for monitoring dashboards

### 2. Diagnostic Function (`src/db.py`)

Added `diagnose_approvals_query(shift_id)` that runs 6 progressive tests:

1. ✅ **Minimal query** - Basic fetch without joins
2. ❌ **Profiles join** - Tests broken `approver:profiles(*)` join (expected to fail)
3. ✅ **Explicit fields** - Tests with specific profile fields
4. ✅ **App_users manual fetch** - Tests recommended approach
5. ℹ️ **Type validation** - Checks shift_id format (UUID vs int)
6. ✅ **No ordering** - Tests if `order()` clause causes issues

**Usage in Streamlit:**
```python
from src.db import diagnose_approvals_query
results = diagnose_approvals_query(shift_id)
st.json(results)
```

### 3. Enhanced Approval Functions

**`get_approvals_by_shift(shift_id, limit=100)`:**
- ✅ Input validation (checks for None, empty, invalid types)
- ✅ UUID format validation
- ✅ Limit parameter to prevent huge payloads (default 100)
- ✅ Manual fetch from `app_users` by `auth_uuid`
- ✅ Comprehensive logging at debug, info, warning levels
- ✅ Graceful error handling with empty list fallback
- ✅ Decorated with error logging and monitoring

**`get_approval(approval_id)`:**
- ✅ Same enhancements as above
- ✅ Additionally fetches shift data if available

### 4. Safe UI Fallback (`pages/10_Admin_Approvals.py`)

The Admin Approvals page now:
- ✅ Wraps approval history in try/except
- ✅ Shows warning if loading fails but allows approval workflow to continue
- ✅ Provides diagnostic button when errors occur
- ✅ Uses `created_at` fallback if `decided_at` doesn't exist

### 5. Integration Tests (`tests/test_approvals.py`)

Comprehensive test suite covering:
- ✅ Valid shift IDs return lists
- ✅ Nonexistent IDs return empty lists without crashing
- ✅ Invalid IDs (None, empty, wrong type) handled gracefully
- ✅ Limit parameter is respected
- ✅ Returned data has expected structure
- ✅ Approver enrichment works correctly
- ✅ Diagnostic function returns proper results

**Run tests:**
```bash
cd /home/user/auditops-streamlit
pytest tests/test_approvals.py -v
```

### 6. SQL Diagnostic Scripts

**`sql_diagnostics/check_approvals_schema.sql`:**
- Inspects table structure and foreign keys
- Checks if `approver_id` matches `profiles` or `app_users`
- Identifies orphaned approver_id values
- Reviews RLS policies
- Provides summary statistics

**Usage:**
```bash
psql $DATABASE_URL -f sql_diagnostics/check_approvals_schema.sql
```

**`sql_diagnostics/fix_approvals_foreign_keys.sql`:**
- Drop broken foreign key to profiles
- Add correct foreign key to app_users (if needed)
- Update RLS policies to allow joins
- Migrate data if approver_id format needs changing
- Verification queries

⚠️ **IMPORTANT:** Review diagnostic results before running fixes!

## 🔍 How to Diagnose Issues

### Step 1: Check Streamlit Cloud Logs

1. Go to Streamlit Cloud → Manage app → Logs
2. Search for `[PostgREST Error]` or `[DIAGNOSTIC]`
3. Look for the full unredacted error message
4. Download logs if needed

### Step 2: Check Local Error Logs

```bash
cat /tmp/postgrest_errors.log
```

This file contains full error details that Streamlit redacts.

### Step 3: Run Diagnostic Function

In your Streamlit app or Python console:

```python
from src.db import diagnose_approvals_query
results = diagnose_approvals_query("your-shift-id-here")
print(results)
```

Look for which tests pass/fail to isolate the issue.

### Step 4: Run SQL Diagnostics

```bash
# Run via psql
psql $DATABASE_URL -f sql_diagnostics/check_approvals_schema.sql > diagnostic_output.txt

# Or copy queries to Supabase SQL Editor
```

Review output to identify:
- Whether `approver_id` references `profiles` or `app_users`
- If foreign keys are properly configured
- If RLS policies are blocking joins
- If there are orphaned references

### Step 5: Test with cURL

```bash
# Replace placeholders with your actual values
SUPABASE_URL="https://your-project.supabase.co"
ANON_KEY="your-anon-key"
SHIFT_ID="actual-shift-id"

# Test basic query (should work)
curl -H "apikey: $ANON_KEY" \
     -H "Authorization: Bearer $ANON_KEY" \
     "$SUPABASE_URL/rest/v1/approvals?select=*&shift_id=eq.$SHIFT_ID"

# Test with profiles join (may fail)
curl -H "apikey: $ANON_KEY" \
     -H "Authorization: Bearer $ANON_KEY" \
     "$SUPABASE_URL/rest/v1/approvals?select=*,approver:profiles(*)&shift_id=eq.$SHIFT_ID"
```

The second query will show the actual PostgREST error message.

## 🔧 How to Apply Fixes

### If Foreign Key is Broken

1. Review diagnostic output from SQL scripts
2. Uncomment relevant sections in `fix_approvals_foreign_keys.sql`
3. Run the fix script (or copy to Supabase SQL Editor)
4. Verify with test queries at end of script

### If RLS is Blocking

```sql
-- Allow authenticated users to view profiles
CREATE POLICY "Profiles viewable by authenticated users"
ON profiles FOR SELECT
TO authenticated
USING (true);
```

Or use `service_role=True` in your Python code (already implemented).

### If Data Migration Needed

Follow the commented migration steps in `fix_approvals_foreign_keys.sql`:
1. Backup existing data
2. Update to new format
3. Verify migration
4. Clean up

## 📊 Monitoring & Alerting

### Current Logging

All errors are logged to:
- Console output (visible in Streamlit Cloud logs)
- `/tmp/postgrest_errors.log` file
- Python logging system

Search for:
- `[PostgREST Error]` - Full APIError details
- `[MONITOR]` - High-level error tracking
- `[DB]` - Database operation logs
- `[DIAGNOSTIC]` - Diagnostic test results

### Future Enhancements

The `@track_api_errors` decorator is ready for integration with:

```python
# In src/db.py, uncomment and configure:
import sentry_sdk
sentry_sdk.capture_exception(e)

# Or integrate with CloudWatch, Datadog, etc.
```

## ✅ Verification Checklist

After applying fixes:

- [ ] Run diagnostic SQL script and review output
- [ ] Run `diagnose_approvals_query()` in app - all tests should pass
- [ ] Test Admin Approvals page - should load without errors
- [ ] Check logs for any PostgREST errors
- [ ] Run integration tests: `pytest tests/test_approvals.py -v`
- [ ] Verify approver names display correctly (not "Unknown")
- [ ] Test approval workflow end-to-end
- [ ] Monitor logs for 24 hours to ensure no recurrence

## 📚 Additional Resources

### Understanding PostgREST Foreign Key Syntax

```python
# Correct syntax: alias:foreign_table(fields)
.select("*, approver:profiles(*)")
# Creates nested object: approval['approver'] = profile data

# The foreign key must exist in database:
# approvals.approver_id -> profiles.id (or whatever column)
```

### Common Error Patterns

1. **"relation does not exist"** → Table name is wrong
2. **"column does not exist"** → Field name is wrong in select()
3. **"could not find foreign key"** → FK doesn't exist or alias is wrong
4. **Empty response with no error** → RLS is blocking the query

### Quick Reference Commands

```bash
# View logs
tail -f /tmp/postgrest_errors.log

# Run tests
pytest tests/test_approvals.py -v

# Run SQL diagnostics
psql $DATABASE_URL -f sql_diagnostics/check_approvals_schema.sql

# Check Streamlit Cloud logs
# Dashboard → Manage app → Logs → Search for "[PostgREST Error]"
```

## 🎯 Summary

This comprehensive implementation provides:

1. **Immediate fix** - Approvals page works correctly
2. **Diagnostic tools** - Quickly identify future issues
3. **Robust error handling** - App doesn't crash on errors
4. **Comprehensive logging** - Full visibility into errors
5. **Tests** - Prevent regressions
6. **SQL tools** - Database-level diagnostics and fixes
7. **Documentation** - Easy troubleshooting for future issues

The root cause (broken foreign key join) has been fixed by using manual fetches from `app_users` table instead of relying on PostgREST's automatic joins.
