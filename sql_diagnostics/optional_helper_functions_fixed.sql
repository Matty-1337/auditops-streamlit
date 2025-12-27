-- ============================================
-- OPTIONAL: Fixed Helper Functions for Pay Periods
-- ============================================
-- NOTE: These are NOT required for the application to work!
-- The Admin Pay Periods page has its own logic to find current period.
-- Only run this if you want to use these functions for direct SQL queries.

-- ============================================
-- OPTION 1: Functions that return ALL columns using *
-- ============================================
-- This avoids specifying individual column names

CREATE OR REPLACE FUNCTION get_current_pay_period()
RETURNS SETOF pay_periods AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM pay_periods
    WHERE CURRENT_DATE BETWEEN start_date AND end_date
    ORDER BY start_date
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_next_pay_period()
RETURNS SETOF pay_periods AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM pay_periods
    WHERE start_date > CURRENT_DATE
    ORDER BY start_date
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Test the functions
SELECT 'Testing get_current_pay_period():' AS test;
SELECT * FROM get_current_pay_period();

SELECT 'Testing get_next_pay_period():' AS test;
SELECT * FROM get_next_pay_period();

-- ============================================
-- OPTION 2: Simple queries (no functions needed)
-- ============================================
-- You can just use these queries directly instead of functions:

-- Get current pay period
SELECT * FROM pay_periods
WHERE CURRENT_DATE BETWEEN start_date AND end_date
ORDER BY start_date
LIMIT 1;

-- Get next pay period
SELECT * FROM pay_periods
WHERE start_date > CURRENT_DATE
ORDER BY start_date
LIMIT 1;
