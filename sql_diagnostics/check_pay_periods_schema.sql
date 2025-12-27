-- Diagnostic script to check pay_periods table schema and permissions
-- Run this in Supabase SQL Editor to verify everything is set up correctly

-- 1. Check if pay_periods table exists
SELECT
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_name = 'pay_periods';

-- 2. Check pay_periods table columns
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pay_periods'
ORDER BY ordinal_position;

-- 3. Check constraints on pay_periods
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
LEFT JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.table_name = 'pay_periods';

-- 4. Check RLS policies on pay_periods
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'pay_periods';

-- 5. Check if RLS is enabled
SELECT
    tablename,
    rowsecurity
FROM pg_tables
WHERE tablename = 'pay_periods';

-- 6. List existing pay periods (if any)
SELECT
    id,
    start_date,
    end_date,
    status,
    created_at,
    updated_at
FROM pay_periods
ORDER BY start_date DESC
LIMIT 10;

-- 7. Check for uuid-ossp extension
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'uuid-ossp';

-- 8. Test if we can insert a pay period (ROLLBACK to not actually create it)
BEGIN;
INSERT INTO pay_periods (start_date, end_date, status)
VALUES ('2025-01-01', '2025-01-15', 'open')
RETURNING *;
ROLLBACK;

-- 9. Check if there's a duplicate entry for the dates in question
SELECT
    id,
    start_date,
    end_date,
    status,
    created_at
FROM pay_periods
WHERE
    start_date = '2025-12-25'
    AND end_date = '2026-01-09';
