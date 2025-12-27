-- Fix script for pay_periods table
-- Run this in Supabase SQL Editor if the pay_periods table has issues

-- Ensure uuid-ossp extension is enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop and recreate pay_periods table (CAUTION: This will delete all existing data!)
-- Comment out the DROP if you want to preserve existing data
-- DROP TABLE IF EXISTS pay_periods CASCADE;

-- Create pay_periods table (IF NOT EXISTS will skip if it already exists)
CREATE TABLE IF NOT EXISTS pay_periods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'locked')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(start_date, end_date)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_pay_periods_dates ON pay_periods(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_pay_periods_status ON pay_periods(status);

-- Enable RLS
ALTER TABLE pay_periods ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "All authenticated users can view pay periods" ON pay_periods;
DROP POLICY IF EXISTS "Admins can manage pay periods" ON pay_periods;

-- Recreate policies
CREATE POLICY "All authenticated users can view pay periods" ON pay_periods
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Admins can manage pay periods" ON pay_periods
    FOR ALL USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN'
    ));

-- Create or replace trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists and recreate
DROP TRIGGER IF EXISTS update_pay_periods_updated_at ON pay_periods;
CREATE TRIGGER update_pay_periods_updated_at BEFORE UPDATE ON pay_periods
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Verify the setup
SELECT
    'pay_periods table created successfully' AS status,
    COUNT(*) AS existing_periods
FROM pay_periods;

-- Show the table structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'pay_periods'
ORDER BY ordinal_position;
