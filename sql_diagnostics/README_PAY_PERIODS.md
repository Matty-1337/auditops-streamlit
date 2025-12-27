# Recurring Pay Periods Setup

## Overview

This system automatically generates bi-weekly pay periods following a fixed schedule:

- **Period Length**: 14 days (Saturday to Friday)
- **Pay Date**: The Friday following the period end (7 days after)
- **First Period**: December 27, 2025 - January 9, 2026 → Pay Date: January 16, 2026
- **Recurrence**: Every 14 days, indefinitely

## Schedule Example

| Period | Start (Saturday) | End (Friday) | Pay Date (Friday) |
|--------|------------------|--------------|-------------------|
| 1      | Dec 27, 2025     | Jan 9, 2026  | Jan 16, 2026      |
| 2      | Jan 10, 2026     | Jan 23, 2026 | Jan 30, 2026      |
| 3      | Jan 24, 2026     | Feb 6, 2026  | Feb 13, 2026      |
| ...    | ...              | ...          | ...               |

## Setup Instructions

### Step 1: Run the Setup Script

1. Go to your **Supabase Project** → **SQL Editor**
2. Open the file: `sql_diagnostics/setup_recurring_pay_periods.sql`
3. Copy the entire contents
4. Paste into the SQL Editor
5. Click **Run**

This will:
- Add the `pay_date` column to the `pay_periods` table
- Create functions to generate pay periods
- Populate ~130 pay periods (~5 years worth)
- Set up helper functions

### Step 2: Verify the Setup

After running the script, you should see output showing:
- Number of periods created
- First and last pay period dates
- Sample pay periods with validation

You can also verify in the Streamlit app:
1. Go to **Admin Pay Periods** page
2. You should see all pre-generated pay periods
3. Each period should show: Start Date, End Date, Pay Date, Status

### Step 3: Deploy Application Changes

The application code has been updated to support pay dates. Deploy/restart your Streamlit app to see the changes.

## Database Schema

The `pay_periods` table now includes:

```sql
CREATE TABLE pay_periods (
    id UUID PRIMARY KEY,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    pay_date DATE NOT NULL,    -- NEW: When payment is issued
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(start_date, end_date),
    CHECK (end_date > start_date),
    CHECK (pay_date > end_date)
);
```

## SQL Functions Created

### 1. `generate_pay_periods(num_periods)`
Generates pay period data without inserting to database.

```sql
-- Generate next 52 periods (1 year)
SELECT * FROM generate_pay_periods(52);
```

### 2. `populate_pay_periods(num_periods, clear_existing)`
Inserts pay periods into the database.

```sql
-- Add 26 more periods (6 months)
SELECT * FROM populate_pay_periods(26, FALSE);
```

### 3. `get_current_pay_period()`
Returns the pay period for today's date.

```sql
SELECT * FROM get_current_pay_period();
```

### 4. `get_next_pay_period()`
Returns the next upcoming pay period.

```sql
SELECT * FROM get_next_pay_period();
```

## Maintenance

### Adding More Pay Periods

To extend beyond the initial 5 years:

```sql
-- Add 26 more periods (6 months)
SELECT * FROM populate_pay_periods(26, FALSE);
```

### Clearing and Regenerating

**⚠️ WARNING**: This will delete all existing pay periods and associated data!

```sql
-- Clear and regenerate all periods
SELECT * FROM populate_pay_periods(130, TRUE);
```

### Checking for Gaps

```sql
-- Find gaps in the pay period sequence
WITH period_gaps AS (
    SELECT
        start_date,
        end_date,
        LEAD(start_date) OVER (ORDER BY start_date) AS next_start
    FROM pay_periods
)
SELECT *
FROM period_gaps
WHERE next_start IS NOT NULL
  AND next_start != end_date + 1;
```

## Troubleshooting

### Issue: Pay periods not showing in app

**Solution**: Ensure you've:
1. Run the SQL setup script
2. Restarted your Streamlit app
3. Cleared browser cache

### Issue: Duplicate key error when adding periods

**Solution**: This is normal if periods already exist. The script skips duplicates.

### Issue: Pay date is NULL for existing periods

**Solution**: Run this update query:

```sql
UPDATE pay_periods
SET pay_date = end_date + INTERVAL '7 days'
WHERE pay_date IS NULL;
```

## Schedule Validation

To verify the schedule is correct:

```sql
SELECT
    start_date,
    end_date,
    pay_date,
    -- Validate: start_date should be Saturday (day 6)
    EXTRACT(DOW FROM start_date) AS start_dow,
    -- Validate: end_date should be Friday (day 5)
    EXTRACT(DOW FROM end_date) AS end_dow,
    -- Validate: pay_date should be Friday (day 5)
    EXTRACT(DOW FROM pay_date) AS pay_dow,
    -- Validate: period should be 14 days
    (end_date - start_date) AS days_in_period,
    -- Validate: 7 days from end to pay
    (pay_date - end_date) AS days_to_pay
FROM pay_periods
WHERE
    -- Check for any violations
    EXTRACT(DOW FROM start_date) != 6  -- Not Saturday
    OR EXTRACT(DOW FROM end_date) != 5   -- Not Friday
    OR EXTRACT(DOW FROM pay_date) != 5   -- Not Friday
    OR (end_date - start_date) != 13     -- Not 14 days
    OR (pay_date - end_date) != 7        -- Not 7 days after
ORDER BY start_date;
```

If this returns no rows, your schedule is correct!

## Support

For issues or questions, contact the system administrator or check:
- Supabase logs for SQL errors
- Streamlit app logs for application errors
- `/tmp/postgrest_errors.log` for API errors
