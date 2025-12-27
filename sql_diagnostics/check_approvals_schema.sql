-- ============================================
-- Approvals Table Diagnostic Queries
-- ============================================
-- Run these queries to diagnose issues with the approvals table,
-- foreign keys, and PostgREST joins.
--
-- Usage:
--   psql $DATABASE_URL -f sql_diagnostics/check_approvals_schema.sql
--   OR run via Supabase SQL Editor
-- ============================================

-- 1. Check approvals table structure
\echo '=== 1. Approvals Table Structure ==='
\d+ approvals

-- 2. Check all foreign keys on approvals table
\echo ''
\echo '=== 2. Foreign Keys on Approvals Table ==='
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'approvals'
    AND tc.constraint_type = 'FOREIGN KEY';

-- 3. Check what approver_id actually contains (sample data)
\echo ''
\echo '=== 3. Sample approver_id Values ==='
SELECT id, shift_id, approver_id, decision, created_at
FROM approvals
ORDER BY created_at DESC
LIMIT 5;

-- 4. Check if approver_id matches profiles.id or profiles.user_id
\echo ''
\echo '=== 4. Check Approver Match in Profiles Table ==='
SELECT
    a.id as approval_id,
    a.approver_id,
    p.id as profile_id,
    p.user_id as profile_user_id,
    p.full_name as profile_name
FROM approvals a
LEFT JOIN profiles p ON p.user_id = a.approver_id
ORDER BY a.created_at DESC
LIMIT 5;

-- 5. Check if approver_id matches app_users.auth_uuid
\echo ''
\echo '=== 5. Check Approver Match in App_Users Table ==='
SELECT
    a.id as approval_id,
    a.approver_id,
    u.id as app_user_id,
    u.auth_uuid,
    u.name as app_user_name
FROM approvals a
LEFT JOIN app_users u ON u.auth_uuid = a.approver_id
ORDER BY a.created_at DESC
LIMIT 5;

-- 6. Check for orphaned approver_id values (not in profiles or app_users)
\echo ''
\echo '=== 6. Orphaned Approver IDs (Not Found in Either Table) ==='
SELECT
    a.id as approval_id,
    a.approver_id,
    a.decision,
    CASE
        WHEN p.user_id IS NOT NULL THEN 'Found in profiles'
        WHEN u.auth_uuid IS NOT NULL THEN 'Found in app_users'
        ELSE 'ORPHANED - Not found in any user table'
    END as status
FROM approvals a
LEFT JOIN profiles p ON p.user_id = a.approver_id
LEFT JOIN app_users u ON u.auth_uuid = a.approver_id
WHERE p.user_id IS NULL AND u.auth_uuid IS NULL
LIMIT 10;

-- 7. Check RLS policies on approvals table
\echo ''
\echo '=== 7. Row Level Security Policies on Approvals ==='
SELECT * FROM pg_policies WHERE tablename = 'approvals';

-- 8. Check RLS policies on profiles table (may block joins)
\echo ''
\echo '=== 8. Row Level Security Policies on Profiles ==='
SELECT * FROM pg_policies WHERE tablename = 'profiles';

-- 9. Check if RLS is enabled on tables
\echo ''
\echo '=== 9. RLS Status on Related Tables ==='
SELECT
    schemaname,
    tablename,
    relrowsecurity as rls_enabled,
    relforcerowsecurity as rls_forced
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE relname IN ('approvals', 'profiles', 'app_users', 'shifts')
    AND n.nspname = 'public';

-- 10. Test data integrity: shifts referenced by approvals
\echo ''
\echo '=== 10. Check for Approvals with Invalid Shift References ==='
SELECT
    a.id as approval_id,
    a.shift_id,
    s.id as shift_exists
FROM approvals a
LEFT JOIN shifts s ON s.id = a.shift_id
WHERE s.id IS NULL
LIMIT 5;

-- 11. Summary statistics
\echo ''
\echo '=== 11. Approvals Summary Statistics ==='
SELECT
    COUNT(*) as total_approvals,
    COUNT(DISTINCT shift_id) as unique_shifts,
    COUNT(DISTINCT approver_id) as unique_approvers,
    COUNT(CASE WHEN decision = 'approved' THEN 1 END) as approved_count,
    COUNT(CASE WHEN decision = 'rejected' THEN 1 END) as rejected_count
FROM approvals;

-- 12. Recent approvals with full details
\echo ''
\echo '=== 12. Recent Approvals (Without Joins) ==='
SELECT
    id,
    shift_id,
    approver_id,
    decision,
    decision_notes,
    created_at
FROM approvals
ORDER BY created_at DESC
LIMIT 10;

\echo ''
\echo '=== Diagnostic Complete ==='
\echo 'Review the results above to identify:'
\echo '  - Whether approver_id should reference profiles or app_users'
\echo '  - If foreign keys are properly configured'
\echo '  - If RLS policies are blocking joins'
\echo '  - If there are orphaned or invalid references'
