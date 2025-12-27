-- ============================================
-- Fix Approvals Foreign Key Relationships
-- ============================================
-- Run these queries ONLY AFTER reviewing the diagnostic results
-- from check_approvals_schema.sql
--
-- IMPORTANT: Review and uncomment only the sections that apply
-- to your specific issue. Do NOT run all commands blindly.
--
-- Usage:
--   psql $DATABASE_URL -f sql_diagnostics/fix_approvals_foreign_keys.sql
--   OR run via Supabase SQL Editor (copy sections as needed)
-- ============================================

-- ============================================
-- FIX 1: Remove Broken Foreign Key to Profiles
-- ============================================
-- Run this if approver_id should NOT reference profiles table

-- Check existing foreign keys first
SELECT conname FROM pg_constraint
WHERE conrelid = 'approvals'::regclass
  AND contype = 'f'
  AND conname LIKE '%approver%';

-- Uncomment to drop broken FK (CAUTION!)
-- ALTER TABLE approvals
-- DROP CONSTRAINT IF EXISTS approvals_approver_id_fkey;

-- ALTER TABLE approvals
-- DROP CONSTRAINT IF EXISTS fk_approvals_approver;


-- ============================================
-- FIX 2: Add Foreign Key to app_users (if needed)
-- ============================================
-- Run this if approver_id should reference app_users.auth_uuid

-- First, ensure app_users.auth_uuid has a unique index
-- (Required for foreign key reference)

-- Check if index exists
SELECT indexname FROM pg_indexes
WHERE tablename = 'app_users'
  AND indexname LIKE '%auth_uuid%';

-- Uncomment to create unique index (if it doesn't exist)
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_auth_uuid
-- ON app_users(auth_uuid);

-- Uncomment to add foreign key constraint
-- ALTER TABLE approvals
-- ADD CONSTRAINT fk_approvals_approver_app_users
-- FOREIGN KEY (approver_id)
-- REFERENCES app_users(auth_uuid)
-- ON DELETE SET NULL;


-- ============================================
-- FIX 3: Update RLS Policies (if joins are blocked)
-- ============================================
-- Run this if RLS is preventing PostgREST joins

-- Check existing policies
SELECT policyname, permissive, roles, cmd
FROM pg_policies
WHERE tablename = 'profiles';

-- Option A: Allow authenticated users to view profiles
-- Uncomment to create policy
-- CREATE POLICY "Profiles viewable by authenticated users"
-- ON profiles FOR SELECT
-- TO authenticated
-- USING (true);

-- Option B: Allow public (anon) users to view profiles
-- (Less secure - use only if necessary)
-- Uncomment to create policy
-- CREATE POLICY "Profiles publicly readable"
-- ON profiles FOR SELECT
-- TO anon
-- USING (true);

-- Option C: Allow service role full access
-- Uncomment to create policy
-- CREATE POLICY "Service role full access to profiles"
-- ON profiles
-- TO service_role
-- USING (true)
-- WITH CHECK (true);


-- ============================================
-- FIX 4: Data Migration (if needed)
-- ============================================
-- If approver_id format needs to change

-- Example: Convert approver_id from profiles.id to app_users.auth_uuid
-- CAUTION: Only run if you've verified this is needed!

-- Preview the migration (read-only)
SELECT
    a.id as approval_id,
    a.approver_id as old_approver_id,
    u.auth_uuid as new_approver_id
FROM approvals a
JOIN profiles p ON p.id = a.approver_id
JOIN app_users u ON u.id = p.user_id
LIMIT 5;

-- Uncomment to perform migration (CAUTION - creates backup first!)
-- -- Step 1: Add backup column
-- ALTER TABLE approvals ADD COLUMN IF NOT EXISTS approver_id_backup TEXT;
--
-- -- Step 2: Backup existing values
-- UPDATE approvals SET approver_id_backup = approver_id;
--
-- -- Step 3: Update to new format
-- UPDATE approvals a
-- SET approver_id = u.auth_uuid
-- FROM profiles p
-- JOIN app_users u ON u.id = p.user_id
-- WHERE a.approver_id = p.id::text;
--
-- -- Step 4: Verify (check that all were updated)
-- SELECT COUNT(*) as unmigrated FROM approvals WHERE approver_id_backup IS NOT NULL AND approver_id = approver_id_backup;
--
-- -- Step 5: Once verified, optionally drop backup column
-- -- ALTER TABLE approvals DROP COLUMN approver_id_backup;


-- ============================================
-- FIX 5: Ensure shift_id Foreign Key is Valid
-- ============================================

-- Check if shift_id foreign key exists
SELECT conname FROM pg_constraint
WHERE conrelid = 'approvals'::regclass
  AND contype = 'f'
  AND conname LIKE '%shift%';

-- Uncomment to add if missing
-- ALTER TABLE approvals
-- ADD CONSTRAINT fk_approvals_shift
-- FOREIGN KEY (shift_id)
-- REFERENCES shifts(id)
-- ON DELETE CASCADE;


-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- Run these after applying fixes to verify everything works

-- Test 1: Verify foreign keys are correct
SELECT
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_name = 'approvals'
    AND tc.constraint_type = 'FOREIGN KEY';

-- Test 2: Verify all approver_ids can be resolved
SELECT
    COUNT(*) as total,
    COUNT(u.auth_uuid) as found_in_app_users,
    COUNT(*) - COUNT(u.auth_uuid) as orphaned
FROM approvals a
LEFT JOIN app_users u ON u.auth_uuid = a.approver_id;

-- Test 3: Sample join to verify it works
SELECT
    a.id,
    a.decision,
    u.name as approver_name
FROM approvals a
LEFT JOIN app_users u ON u.auth_uuid = a.approver_id
LIMIT 5;

\echo ''
\echo '=== Fix Script Complete ==='
\echo 'Review verification queries above to ensure fixes were successful.'
\echo 'Test your Streamlit app to confirm the APIError is resolved.'
