-- AuditOps Database Schema
-- Run this in your Supabase SQL Editor to set up all tables, indexes, and RLS policies

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- PROFILES TABLE
-- ============================================
-- Note: id should match auth.users.id (UUID from Supabase Auth)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'MANAGER', 'AUDITOR')),
    team_id UUID, -- Optional: for grouping users into teams (managers can see their team)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role);
CREATE INDEX IF NOT EXISTS idx_profiles_is_active ON profiles(is_active);
CREATE INDEX IF NOT EXISTS idx_profiles_team_id ON profiles(team_id);

-- ============================================
-- CLIENTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    address TEXT,
    notes TEXT,
    manager_id UUID REFERENCES profiles(id) ON DELETE SET NULL, -- Manager who oversees this client
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_clients_is_active ON clients(is_active);
CREATE INDEX IF NOT EXISTS idx_clients_manager_id ON clients(manager_id);

-- ============================================
-- SHIFTS TABLE (also called "jobs" in some contexts)
-- ============================================
CREATE TABLE IF NOT EXISTS shifts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    auditor_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    manager_id UUID REFERENCES profiles(id) ON DELETE SET NULL, -- Manager overseeing this shift/job
    check_in TIMESTAMPTZ NOT NULL,
    check_out TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'approved', 'rejected')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shifts_auditor_id ON shifts(auditor_id);
CREATE INDEX IF NOT EXISTS idx_shifts_client_id ON shifts(client_id);
CREATE INDEX IF NOT EXISTS idx_shifts_manager_id ON shifts(manager_id);
CREATE INDEX IF NOT EXISTS idx_shifts_status ON shifts(status);
CREATE INDEX IF NOT EXISTS idx_shifts_check_in ON shifts(check_in);

-- ============================================
-- PAY PERIODS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS pay_periods (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'locked')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(start_date, end_date)
);

CREATE INDEX IF NOT EXISTS idx_pay_periods_dates ON pay_periods(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_pay_periods_status ON pay_periods(status);

-- ============================================
-- PAY ITEMS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS pay_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pay_period_id UUID NOT NULL REFERENCES pay_periods(id) ON DELETE CASCADE,
    auditor_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    shift_id UUID REFERENCES shifts(id) ON DELETE SET NULL,
    hours DECIMAL(10, 2) NOT NULL,
    rate DECIMAL(10, 2) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pay_items_pay_period_id ON pay_items(pay_period_id);
CREATE INDEX IF NOT EXISTS idx_pay_items_auditor_id ON pay_items(auditor_id);
CREATE INDEX IF NOT EXISTS idx_pay_items_shift_id ON pay_items(shift_id);

-- ============================================
-- APPROVALS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    shift_id UUID NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    approver_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    decision_notes TEXT,
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approvals_shift_id ON approvals(shift_id);
CREATE INDEX IF NOT EXISTS idx_approvals_approver_id ON approvals(approver_id);
CREATE INDEX IF NOT EXISTS idx_approvals_decision ON approvals(decision);

-- ============================================
-- ACCESS LOGS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    object_path TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('view', 'download', 'upload')),
    ip_optional TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_access_logs_user_id ON access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_client_id ON access_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_access_logs_created_at ON access_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_access_logs_action ON access_logs(action);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================
-- Note: These are basic policies. Adjust based on your security requirements.

-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE shifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pay_periods ENABLE ROW LEVEL SECURITY;
ALTER TABLE pay_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can read their own profile, admins can read all
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id OR EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN'
    ));

-- Clients: All authenticated users can view active clients
-- Managers can view clients they manage or all if admin
CREATE POLICY "Authenticated users can view active clients" ON clients
    FOR SELECT USING (
        auth.role() = 'authenticated' 
        AND is_active = TRUE
        AND (
            -- Admins see all
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN')
            OR
            -- Managers see clients they manage
            manager_id = auth.uid()
            OR
            -- Auditors see all active clients (for check-in selection)
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'AUDITOR')
        )
    );

-- Clients: Only admins can insert/update/delete
CREATE POLICY "Admins can manage clients" ON clients
    FOR ALL USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN'
    ));

-- Shifts: Auditors can view/manage their own shifts
-- Managers can view shifts for their team/clients
CREATE POLICY "Auditors can view own shifts" ON shifts
    FOR SELECT USING (
        auditor_id = auth.uid() 
        OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN')
        OR (
            -- Managers can see shifts they manage or shifts for clients they manage
            EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'MANAGER')
            AND (manager_id = auth.uid() OR EXISTS (
                SELECT 1 FROM clients WHERE id = shifts.client_id AND manager_id = auth.uid()
            ))
        )
    );

CREATE POLICY "Auditors can insert own shifts" ON shifts
    FOR INSERT WITH CHECK (auditor_id = auth.uid());

CREATE POLICY "Auditors can update own draft shifts" ON shifts
    FOR UPDATE USING (auditor_id = auth.uid() AND status = 'draft');

-- Managers and admins can update submitted shifts
CREATE POLICY "Managers can update submitted shifts" ON shifts
    FOR UPDATE USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('ADMIN', 'MANAGER')
    ) AND status = 'submitted');

-- Pay periods: Admins can manage, all can view
CREATE POLICY "All authenticated users can view pay periods" ON pay_periods
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Admins can manage pay periods" ON pay_periods
    FOR ALL USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN'
    ));

-- Pay items: Auditors can view their own, admins can view all
CREATE POLICY "Users can view own pay items" ON pay_items
    FOR SELECT USING (auditor_id = auth.uid() OR EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN'
    ));

-- Approvals: Managers and admins can view and create
CREATE POLICY "Managers can manage approvals" ON approvals
    FOR ALL USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('ADMIN', 'MANAGER')
    ));

-- Access logs: Only admins can view
CREATE POLICY "Admins can view access logs" ON access_logs
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'ADMIN'
    ));

-- Access logs: System can insert (via service role)
CREATE POLICY "System can insert access logs" ON access_logs
    FOR INSERT WITH CHECK (true);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shifts_updated_at BEFORE UPDATE ON shifts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pay_periods_updated_at BEFORE UPDATE ON pay_periods
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- FIRST ADMIN BOOTSTRAP FUNCTION
-- ============================================
-- This function helps create the first admin user safely.
-- Usage: After creating a user in Supabase Auth, call this function to create their profile.
-- Example: SELECT bootstrap_first_admin('<auth-user-uuid>', 'admin@example.com', 'Admin User');

CREATE OR REPLACE FUNCTION bootstrap_first_admin(
    user_id UUID,
    user_email TEXT,
    user_full_name TEXT
)
RETURNS UUID AS $$
DECLARE
    admin_count INTEGER;
    profile_id UUID;
BEGIN
    -- Check if any admin exists
    SELECT COUNT(*) INTO admin_count
    FROM profiles
    WHERE role = 'ADMIN';
    
    -- Only allow if no admin exists yet, OR if the user_id already has a profile
    IF admin_count > 0 AND NOT EXISTS (SELECT 1 FROM profiles WHERE id = user_id) THEN
        RAISE EXCEPTION 'An admin already exists. Use regular profile creation instead.';
    END IF;
    
    -- Insert or update profile
    INSERT INTO profiles (id, email, full_name, role, is_active)
    VALUES (user_id, user_email, user_full_name, 'ADMIN', TRUE)
    ON CONFLICT (id) DO UPDATE
    SET 
        email = EXCLUDED.email,
        full_name = EXCLUDED.full_name,
        role = 'ADMIN',
        is_active = TRUE,
        updated_at = NOW()
    RETURNING id INTO profile_id;
    
    RETURN profile_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users (they'll use service role in practice)
GRANT EXECUTE ON FUNCTION bootstrap_first_admin(UUID, TEXT, TEXT) TO authenticated;

-- ============================================
-- INITIAL DATA (Optional - for testing)
-- ============================================
-- Note: You'll need to create users via Supabase Auth first, then link them to profiles
-- 
-- Method 1: Use the bootstrap function (recommended for first admin)
-- After creating a user in Supabase Auth Dashboard:
-- SELECT bootstrap_first_admin('<user-uuid-from-auth>', 'admin@example.com', 'Admin User');
--
-- Method 2: Direct insert (for subsequent users, or if you have service role access)
-- INSERT INTO profiles (id, email, full_name, role) 
-- VALUES ('<user-uuid-from-auth>', 'admin@example.com', 'Admin User', 'ADMIN');
--
-- Method 3: Via Supabase Dashboard SQL Editor with service role
-- Use the service_role key to bypass RLS and insert directly

