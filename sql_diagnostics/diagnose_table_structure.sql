-- ============================================
-- DIAGNOSTIC: Check actual pay_periods table structure
-- ============================================
-- Run this to see what columns your table actually has

SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pay_periods'
ORDER BY ordinal_position;

-- Check if id column exists
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'pay_periods' AND column_name = 'id'
        ) THEN '✅ id column EXISTS'
        ELSE '❌ id column MISSING'
    END AS id_column_status;

-- Show sample data from pay_periods (first 5 rows)
SELECT * FROM pay_periods ORDER BY start_date LIMIT 5;
