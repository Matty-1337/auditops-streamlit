-- ============================================
-- RECURRING PAY PERIODS SETUP
-- ============================================
-- This script sets up automatic bi-weekly pay periods
-- Schedule: Saturday to Friday (14 days), pay the following Friday
-- First period: Dec 27, 2025 (Sat) - Jan 9, 2026 (Fri) → Pay: Jan 16, 2026
-- Continues every 14 days indefinitely

-- ============================================
-- STEP 1: Ensure required columns exist
-- ============================================

-- Enable uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add id column if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_periods' AND column_name = 'id'
    ) THEN
        -- Add id column
        ALTER TABLE pay_periods ADD COLUMN id UUID DEFAULT uuid_generate_v4();
        -- Populate existing rows
        UPDATE pay_periods SET id = uuid_generate_v4() WHERE id IS NULL;
        -- Make it NOT NULL
        ALTER TABLE pay_periods ALTER COLUMN id SET NOT NULL;
        -- Set as primary key (drop existing PK if any)
        BEGIN
            ALTER TABLE pay_periods DROP CONSTRAINT IF EXISTS pay_periods_pkey CASCADE;
        EXCEPTION WHEN OTHERS THEN
            NULL; -- Ignore error if constraint doesn't exist
        END;
        ALTER TABLE pay_periods ADD PRIMARY KEY (id);
        RAISE NOTICE '✅ Added id column as UUID PRIMARY KEY';
    ELSE
        RAISE NOTICE '✅ id column already exists';
    END IF;
END $$;

-- Add status column if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_periods' AND column_name = 'status'
    ) THEN
        ALTER TABLE pay_periods ADD COLUMN status TEXT NOT NULL DEFAULT 'open';
        RAISE NOTICE '✅ Added status column to pay_periods table';
    ELSE
        RAISE NOTICE '✅ status column already exists';
    END IF;
END $$;

-- Add pay_date column if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pay_periods' AND column_name = 'pay_date'
    ) THEN
        ALTER TABLE pay_periods ADD COLUMN pay_date DATE;
        RAISE NOTICE '✅ Added pay_date column to pay_periods table';
    ELSE
        RAISE NOTICE '✅ pay_date column already exists';
    END IF;
END $$;

-- Add check constraints if they don't exist
DO $$
BEGIN
    -- Add constraint: end_date must be after start_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'pay_periods_date_order_check'
        AND table_name = 'pay_periods'
    ) THEN
        ALTER TABLE pay_periods ADD CONSTRAINT pay_periods_date_order_check
            CHECK (end_date > start_date);
    END IF;

    -- Add constraint: pay_date must be after end_date
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'pay_periods_pay_date_check'
        AND table_name = 'pay_periods'
    ) THEN
        ALTER TABLE pay_periods ADD CONSTRAINT pay_periods_pay_date_check
            CHECK (pay_date > end_date);
    END IF;
END $$;

-- Create index on pay_date if it doesn't exist
CREATE INDEX IF NOT EXISTS idx_pay_periods_pay_date ON pay_periods(pay_date);

-- ============================================
-- STEP 2: Update existing pay periods with calculated pay_date
-- ============================================
-- For any existing periods without pay_date, calculate it as 7 days after end_date
UPDATE pay_periods
SET pay_date = end_date + INTERVAL '7 days'
WHERE pay_date IS NULL;

-- Now make pay_date NOT NULL
ALTER TABLE pay_periods ALTER COLUMN pay_date SET NOT NULL;

-- ============================================
-- STEP 3: Create function to generate recurring pay periods
-- ============================================
CREATE OR REPLACE FUNCTION generate_pay_periods(
    num_periods INTEGER DEFAULT 130  -- Default: ~5 years of bi-weekly periods
)
RETURNS TABLE (
    start_date DATE,
    end_date DATE,
    pay_date DATE,
    period_number INTEGER
) AS $$
DECLARE
    base_start_date DATE := '2025-12-27'::DATE;  -- First Saturday (Dec 27, 2025)
    current_start DATE;
    current_end DATE;
    current_pay DATE;
    i INTEGER;
BEGIN
    FOR i IN 0..(num_periods - 1) LOOP
        -- Calculate dates for this period
        current_start := base_start_date + (i * 14);  -- Add 14 days for each period
        current_end := current_start + 13;             -- End 13 days later (14 days total, inclusive)
        current_pay := current_end + 7;                -- Pay date is 7 days after end (next Friday)

        -- Return the period
        start_date := current_start;
        end_date := current_end;
        pay_date := current_pay;
        period_number := i + 1;

        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- STEP 4: Create function to populate pay periods
-- ============================================
CREATE OR REPLACE FUNCTION populate_pay_periods(
    num_periods INTEGER DEFAULT 130,  -- ~5 years
    clear_existing BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    action TEXT,
    periods_created INTEGER,
    periods_skipped INTEGER,
    message TEXT
) AS $$
DECLARE
    v_periods_created INTEGER := 0;
    v_periods_skipped INTEGER := 0;
    period_record RECORD;
BEGIN
    -- Optionally clear existing periods
    IF clear_existing THEN
        DELETE FROM pay_periods;
        action := 'CLEARED';
        message := 'Cleared all existing pay periods';
        RETURN NEXT;
    END IF;

    -- Insert generated periods
    FOR period_record IN
        SELECT * FROM generate_pay_periods(num_periods)
    LOOP
        -- Try to insert, skip if duplicate
        BEGIN
            INSERT INTO pay_periods (start_date, end_date, pay_date, status)
            VALUES (
                period_record.start_date,
                period_record.end_date,
                period_record.pay_date,
                'open'
            );
            v_periods_created := v_periods_created + 1;
        EXCEPTION
            WHEN unique_violation THEN
                v_periods_skipped := v_periods_skipped + 1;
        END;
    END LOOP;

    action := 'POPULATED';
    periods_created := v_periods_created;
    periods_skipped := v_periods_skipped;
    message := format('Created %s periods, skipped %s duplicates', v_periods_created, v_periods_skipped);

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- STEP 5: Populate pay periods for the next 5 years
-- ============================================
-- This will create 130 bi-weekly pay periods (260 weeks / ~5 years)
-- Existing periods will be skipped (no duplicates)
SELECT * FROM populate_pay_periods(130, FALSE);

-- ============================================
-- STEP 6: Verify the setup
-- ============================================
-- Show the first 10 pay periods
SELECT
    start_date,
    end_date,
    pay_date,
    EXTRACT(DOW FROM start_date) AS start_day_of_week,  -- Should be 6 (Saturday)
    EXTRACT(DOW FROM end_date) AS end_day_of_week,      -- Should be 5 (Friday)
    EXTRACT(DOW FROM pay_date) AS pay_day_of_week,      -- Should be 5 (Friday)
    end_date - start_date AS period_length,              -- Should be 13 (14 days inclusive)
    pay_date - end_date AS days_to_pay,                  -- Should be 7
    status
FROM pay_periods
ORDER BY start_date
LIMIT 10;

-- Show summary statistics
SELECT
    COUNT(*) AS total_periods,
    MIN(start_date) AS first_period_start,
    MAX(end_date) AS last_period_end,
    MAX(pay_date) AS last_pay_date,
    COUNT(*) FILTER (WHERE status = 'open') AS open_periods,
    COUNT(*) FILTER (WHERE status = 'locked') AS locked_periods
FROM pay_periods;

-- ============================================
-- STEP 7: Create helper function to get current/next period
-- ============================================
CREATE OR REPLACE FUNCTION get_current_pay_period()
RETURNS TABLE (
    id UUID,
    start_date DATE,
    end_date DATE,
    pay_date DATE,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.start_date,
        p.end_date,
        p.pay_date,
        p.status
    FROM pay_periods p
    WHERE CURRENT_DATE BETWEEN p.start_date AND p.end_date
    ORDER BY p.start_date
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_next_pay_period()
RETURNS TABLE (
    id UUID,
    start_date DATE,
    end_date DATE,
    pay_date DATE,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.start_date,
        p.end_date,
        p.pay_date,
        p.status
    FROM pay_periods p
    WHERE p.start_date > CURRENT_DATE
    ORDER BY p.start_date
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Test the helper functions
SELECT 'Current Pay Period:' AS info;
SELECT * FROM get_current_pay_period();

SELECT 'Next Pay Period:' AS info;
SELECT * FROM get_next_pay_period();

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
SELECT
    '✅ Recurring pay periods setup complete!' AS status,
    'Pay periods generated from Dec 27, 2025 for the next ~5 years' AS message,
    'Schedule: Saturday to Friday (14 days), pay the following Friday' AS schedule;
