# SQL Diagnostic Scripts

This directory contains SQL scripts for diagnosing and fixing database issues related to the approvals table and PostgREST queries.

## Files

### `check_approvals_schema.sql`
**Purpose:** Comprehensive diagnostic queries to identify issues with approvals table.

**What it checks:**
- Table structure and columns
- Foreign key relationships
- Sample data and approver_id values
- Whether approver_id matches profiles or app_users
- Orphaned references
- RLS policies
- Data integrity

**Usage:**
```bash
# Via psql
psql $DATABASE_URL -f sql_diagnostics/check_approvals_schema.sql > diagnostic_results.txt

# Via Supabase SQL Editor
# Copy and paste the contents into the SQL Editor
```

**Safe to run:** ✅ Yes - Read-only queries, no modifications

### `fix_approvals_foreign_keys.sql`
**Purpose:** Fix common foreign key and relationship issues.

**What it can fix:**
- Remove broken foreign key to profiles table
- Add correct foreign key to app_users table
- Update RLS policies to allow joins
- Migrate approver_id data format if needed
- Add missing shift_id foreign key

**Usage:**
```bash
# IMPORTANT: Review diagnostic results FIRST!
# Then uncomment only the sections you need

psql $DATABASE_URL -f sql_diagnostics/fix_approvals_foreign_keys.sql
```

**Safe to run:** ⚠️ **REVIEW FIRST** - Contains commented-out commands that modify database

## Typical Workflow

1. **Run diagnostics:**
   ```bash
   psql $DATABASE_URL -f check_approvals_schema.sql > results.txt
   ```

2. **Review results** to identify the specific issue:
   - Check section "5. Check Approver Match in App_Users Table"
   - Look for orphaned approver_ids in section 6
   - Review foreign keys in section 2
   - Check RLS policies in sections 7-8

3. **Apply fixes:**
   - Open `fix_approvals_foreign_keys.sql`
   - Uncomment ONLY the sections needed for your issue
   - Run the modified script
   - OR copy specific commands to Supabase SQL Editor

4. **Verify:**
   - Run verification queries at end of fix script
   - Test Streamlit app
   - Check that APIError is resolved

## Common Scenarios

### Scenario 1: Foreign Key Points to Wrong Table

**Diagnostic shows:** Section 4 has no matches, Section 5 has matches

**Fix:**
1. Uncomment "FIX 1: Remove Broken Foreign Key to Profiles"
2. Optionally uncomment "FIX 2: Add Foreign Key to app_users"
3. Run script

### Scenario 2: RLS Blocking Joins

**Diagnostic shows:** Strict RLS policies in sections 7-8

**Fix:**
1. Uncomment appropriate policy in "FIX 3: Update RLS Policies"
2. Choose Option A (authenticated), B (public), or C (service_role)
3. Run script

### Scenario 3: Data Format Migration Needed

**Diagnostic shows:** approver_id format doesn't match app_users.auth_uuid

**Fix:**
1. Review migration preview query in "FIX 4: Data Migration"
2. Carefully uncomment migration steps
3. Run one step at a time
4. Verify between steps

## Safety Tips

- ✅ **Always run diagnostics before fixes**
- ✅ **Backup your database before running fixes**
- ✅ **Test fixes in development environment first**
- ✅ **Run verification queries after fixes**
- ⚠️ **Never run fix scripts blindly - review first**
- ⚠️ **Uncomment only the sections you need**
- ⚠️ **Data migrations are irreversible - be careful**

## Troubleshooting

### Can't connect to database
```bash
# Check your DATABASE_URL
echo $DATABASE_URL

# Or get it from Supabase dashboard:
# Project Settings → Database → Connection String
```

### psql command not found
```bash
# Install PostgreSQL client
# Ubuntu/Debian:
sudo apt-get install postgresql-client

# macOS:
brew install postgresql
```

### Using Supabase SQL Editor instead of psql

1. Go to Supabase Dashboard → SQL Editor
2. Copy script contents
3. Paste into new query
4. Click "Run"
5. Review results in output pane

## Additional Resources

- [PostgREST Foreign Key Relationships](https://postgrest.org/en/stable/api.html#resource-embedding)
- [Supabase RLS Policies](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL Foreign Keys](https://www.postgresql.org/docs/current/tutorial-fk.html)

## Support

If you encounter issues:

1. Check `/tmp/postgrest_errors.log` in your Streamlit app
2. Run the diagnostic SQL script
3. Review the `DIAGNOSTIC_GUIDE.md` in project root
4. Check Streamlit Cloud logs for `[PostgREST Error]`
