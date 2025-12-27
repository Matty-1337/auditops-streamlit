-- ============================================
-- FIX: Add missing 'id' column to pay_periods table
-- ============================================
-- This script fixes the "column id does not exist" error
-- by adding the id column to an existing pay_periods table
-- that was created without it.
--
-- Run this in Supabase SQL Editor if you see the error:
-- "KeyError" or "column id does not exist"
-- ============================================

-- Step 1: Check if id column exists
DO $$
BEGIN
    -- Check if id column already exists
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pay_periods' AND column_name = 'id'
    ) THEN
        RAISE NOTICE '✅ id column already exists - no action needed';
    ELSE
        RAISE NOTICE '⚠️ id column is missing - adding it now...';

        -- Step 2: Add id column as UUID with default uuid_generate_v4()
        -- First ensure uuid-ossp extension is enabled
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Add the id column
        ALTER TABLE pay_periods ADD COLUMN id UUID DEFAULT uuid_generate_v4();

        -- Step 3: Populate id for existing rows (in case default didn't apply)
        UPDATE pay_periods SET id = uuid_generate_v4() WHERE id IS NULL;

        -- Step 4: Make id NOT NULL
        ALTER TABLE pay_periods ALTER COLUMN id SET NOT NULL;

        -- Step 5: Set id as PRIMARY KEY
        -- First, drop existing primary key if any
        DO $pk$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname LIKE '%pay_periods_pkey%'
            ) THEN
                ALTER TABLE pay_periods DROP CONSTRAINT pay_periods_pkey CASCADE;
            END IF;
        END $pk$;

        -- Add id as primary key
        ALTER TABLE pay_periods ADD PRIMARY KEY (id);

        RAISE NOTICE '✅ Successfully added id column as UUID PRIMARY KEY';
    END IF;
END $$;

-- Step 6: Verify the fix
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pay_periods'
ORDER BY
    CASE column_name
        WHEN 'id' THEN 1
        WHEN 'start_date' THEN 2
        WHEN 'end_date' THEN 3
        WHEN 'pay_date' THEN 4
        WHEN 'status' THEN 5
        ELSE 99
    END;

-- Step 7: Show sample data to confirm ids are populated
SELECT
    id,
    start_date,
    end_date,
    pay_date,
    status
FROM pay_periods
ORDER BY start_date
LIMIT 5;

-- Step 8: Count total periods with valid ids
SELECT
    COUNT(*) as total_periods,
    COUNT(id) as periods_with_id,
    COUNT(*) - COUNT(id) as periods_missing_id
FROM pay_periods;

-- ============================================
-- Expected Output:
-- ============================================
-- If successful, you should see:
-- 1. Column list showing 'id' as 'uuid' type, NOT NULL
-- 2. Sample data showing UUIDs in the id column
-- 3. Count showing all periods have ids (periods_missing_id = 0)
--
-- After running this script:
-- 1. Refresh the Admin Pay Periods page in your app
-- 2. The error should be gone
-- 3. You should be able to lock periods and view pay items
-- ============================================
