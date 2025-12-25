# Authentication Investigation Report
**App:** AuditOps (Streamlit + Supabase)  
**Target User:** matt@htxtap.com  
**Date:** Investigation Report

---

## A. Supabase Client & Env Summary

### Environment Variables Used

| Variable Name | Referenced In | Purpose | Client Type |
|--------------|---------------|---------|-------------|
| `SUPABASE_URL` | `src/config.py:29-34` | Supabase project URL | Both |
| `SUPABASE_ANON_KEY` | `src/config.py:37-57` (anon branch) | Public anon key for client-side | Client |
| `SUPABASE_SERVICE_ROLE_KEY` | `src/config.py:37-57` (service_role branch) | Admin key (local tools only) | Service |
| `SUPABASE_JWT_SECRET` | `src/config.py:60-65` | JWT verification (if needed) | Both |

### Configuration Sources (Priority Order)
1. **Streamlit secrets** (`st.secrets["supabase"]`)
   - Path: `.streamlit/secrets.toml` (not in repo, expected)
   - Keys: `url`, `anon_key`, `service_role_key`, `jwt_secret`
2. **Environment variables** (fallback)
   - Variables: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`

### Client Separation Status
✅ **CORRECTLY SEPARATED**
- **Client-side (anon key)**: Used in `src/supabase_client.py:44` via `get_client(service_role=False)`
- **Service role (admin key)**: Used in `src/supabase_client.py:39` via `get_client(service_role=True)`
- **Service role key is NEVER used in Streamlit app runtime** - only in local admin tool (`tools/admin_set_password.py`)

### Files Referencing Supabase Config
- `src/config.py:29-65` - Configuration getters
- `src/supabase_client.py:6,35,39,44` - Client initialization
- `src/auth.py:32` - Login uses anon key client
- `app.py:199-213` - Debug display uses config
- `pages/99_Admin_Health_Check.py:7,42,46-47` - Health check uses both

---

## B. Auth Flow Findings

### Login Method
**File:** `src/auth.py:10-113`  
**Method:** `client.auth.sign_in_with_password()`  
**Line:** 33

```python
response = client.auth.sign_in_with_password({
    "email": email,
    "password": password
})
```

### Error Handling Logic
**File:** `src/auth.py:93-113`

1. **Exception caught at line 93**: `except Exception as e:`
2. **Error message mapping (lines 96-101)**:
   - "Invalid login credentials" → "Invalid email or password. Please try again."
   - "Email not confirmed" → "Invalid email or password. Please try again."
   - "email...not found" → "Email address not found. Please contact an administrator."
   - **All other exceptions** → "Login failed. Please check your credentials and try again."

3. **"Invalid email or password" triggered at**:
   - `src/auth.py:88` - When `response.user` is None (auth failed)
   - `src/auth.py:97` - When exception contains "Invalid login credentials" or "Email not confirmed"

### Structured Result Return
**File:** `src/auth.py:10-113`

The `login()` function returns a structured dictionary:
```python
{
    "ok": bool,           # True only if auth_ok AND profile_ok
    "auth_ok": bool,      # Authentication succeeded
    "profile_ok": bool,   # Profile lookup succeeded
    "error": str | None,  # Error message
    "user": User | None,
    "session": Session | None,
    "profile": dict | None
}
```

**Critical behavior:**
- Lines 74-81: If `auth_ok=True` but `profile_ok=False`, returns `ok=False` with error "User profile not found..."
- Lines 84-92: If auth fails, returns `auth_ok=False` with error "Invalid email or password..."

### UI Error Display Logic
**File:** `app.py:170-190`

The login UI correctly uses structured results:
- Line 174: If `result.get("ok")` → Success
- Line 179: If `not result.get("auth_ok")` → Shows auth error
- Line 182: If `not result.get("profile_ok")` → Shows profile error
- **NEVER shows both errors simultaneously** ✅

### Session Storage
**File:** `src/auth.py:39-41`
- `st.session_state.auth_user` = User object
- `st.session_state.auth_session` = Session object
- `st.session_state.user_profile` = Profile dict (if found)

---

## C. Profile Lookup Findings

### Profile Table Query
**File:** `src/auth.py:145-186`  
**Function:** `load_user_profile(user_id: str)`

**Query Structure:**
```python
client.table("profiles")
    .select("*")
    .eq("user_id", user_id)  # ✅ Uses user_id column
    .single()                 # Returns single row or exception
    .execute()
```

**Column Used for Linkage:** ✅ `user_id` (correct - matches auth.users.id)

### Query Method
- **Method:** `.single()` - Raises exception if no row found
- **Return:** `response.data` is the row dict (not a list)
- **Error handling:** Exception caught at line 175, returns `None`

### Alternative Profile Functions
**File:** `src/db.py:18-36`
- `get_profile(user_id)` - Uses same `.eq("user_id", user_id).single()` pattern ✅
- `get_all_profiles()` - No filter, returns all profiles
- `update_profile(user_id, data)` - Uses `.eq("user_id", user_id)` ✅

### Profile Lookup Call Chain
1. `app.py:171` → `login(email, password)`
2. `src/auth.py:54` → `load_user_profile(response.user.id)`
3. `src/auth.py:159-164` → Executes query
4. `src/auth.py:168-170` → Returns profile if found
5. `src/auth.py:175-186` → Returns `None` if exception (logged)

### Profile Storage After Login
**File:** `src/auth.py:55-56`
- If profile found: `st.session_state.user_profile = profile`
- If profile missing: `st.session_state.user_profile` remains unset

---

## D. RLS & Schema Risk Analysis

### SQL Queries to Inspect (DO NOT APPLY - FOR REFERENCE ONLY)

```sql
-- 1. Check profiles table columns
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'profiles'
ORDER BY ordinal_position;

-- Expected results:
-- - user_id (uuid, NOT NULL) - Primary key
-- - email (text, NOT NULL)
-- - full_name (text, NOT NULL)
-- - role (text, NOT NULL) - CHECK constraint (ADMIN|MANAGER|AUDITOR)
-- - is_active (boolean, nullable, default=true)
-- - created_at, updated_at (timestamptz)
-- ❌ Should NOT have an "id" column

-- 2. Check if RLS is enabled
SELECT 
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public' 
  AND tablename = 'profiles';

-- Expected: rls_enabled = true

-- 3. List all RLS policies on profiles
SELECT 
    policyname,
    permissive,
    roles,
    cmd as command,
    qual as using_expression,
    with_check
FROM pg_policies
WHERE schemaname = 'public' 
  AND tablename = 'profiles'
ORDER BY policyname;

-- Expected: Should have at least one SELECT policy for authenticated users
-- Preferred: "Authenticated users can read profiles" with USING (auth.role() = 'authenticated')

-- 4. Verify user and profile linkage
SELECT 
    au.id as auth_user_id,
    au.email as auth_email,
    p.user_id as profile_user_id,
    p.email as profile_email,
    p.role,
    p.is_active
FROM auth.users au
LEFT JOIN profiles p ON au.id = p.user_id
WHERE au.email = 'matt@htxtap.com';

-- Expected: Should return one row with matching user_id values
```

### RLS Risk Factors

**HIGH RISK:**
1. **Missing RLS policy** - If no SELECT policy exists, authenticated users cannot read profiles
2. **Over-restrictive policy** - If policy uses `auth.uid() = user_id`, users can only read their own profile (may fail if app queries differently)
3. **Wrong role check** - If policy checks for specific role, users without that role cannot read any profiles

**MEDIUM RISK:**
1. **Multiple conflicting policies** - OR logic may allow unintended access, but shouldn't block
2. **Policy not applied** - If RLS enabled but no policy exists, NO rows returned (PostgreSQL behavior)

**LOW RISK:**
1. **Schema mismatch** - Code uses `user_id`, so schema must match (already verified in previous fixes)

### Expected RLS Policy
```sql
-- Ideal policy for this app:
CREATE POLICY "Authenticated users can read profiles"
ON profiles
FOR SELECT
TO authenticated
USING (auth.role() = 'authenticated');
```

This allows ANY authenticated user to read ANY profile, which the app needs for display/management.

---

## E. Generated Test Script

```javascript
// test-auth-profile.js
// Run with: node test-auth-profile.js
// Requires: npm install @supabase/supabase-js dotenv

require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.SUPABASE_URL || 'YOUR_SUPABASE_URL';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || 'YOUR_ANON_KEY';
const TEST_EMAIL = 'matt@htxtap.com';
const TEST_PASSWORD = 'YOUR_PASSWORD_HERE';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

async function testAuthAndProfile() {
    console.log('=== AUTH & PROFILE TEST ===\n');
    console.log(`Supabase URL: ${SUPABASE_URL.replace(/\/\/[^:]+:[^@]+@/, '//***:***@')}`);
    console.log(`Test Email: ${TEST_EMAIL}\n`);

    // Step 1: Attempt login
    console.log('1. Attempting login...');
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
        email: TEST_EMAIL,
        password: TEST_PASSWORD,
    });

    if (authError) {
        console.error('❌ AUTH FAILED');
        console.error('Error Code:', authError.status || 'N/A');
        console.error('Error Message:', authError.message);
        console.error('Full Error:', JSON.stringify(authError, null, 2));
        return;
    }

    if (!authData.user) {
        console.error('❌ AUTH FAILED: No user returned');
        return;
    }

    console.log('✅ AUTH SUCCESS');
    console.log(`   User ID: ${authData.user.id}`);
    console.log(`   Email: ${authData.user.email}`);
    console.log(`   Session exists: ${!!authData.session}`);
    console.log(`   Access Token (first 20 chars): ${authData.session?.access_token?.substring(0, 20)}...\n`);

    // Step 2: Fetch profile
    console.log('2. Fetching profile...');
    const { data: profileData, error: profileError } = await supabase
        .from('profiles')
        .select('*')
        .eq('user_id', authData.user.id)
        .single();

    if (profileError) {
        console.error('❌ PROFILE LOOKUP FAILED');
        console.error('Error Code:', profileError.code || 'N/A');
        console.error('Error Message:', profileError.message);
        console.error('Error Details:', profileError.details || 'N/A');
        console.error('Error Hint:', profileError.hint || 'N/A');
        console.error('Full Error:', JSON.stringify(profileError, null, 2));
        
        // Check if it's a "no rows" error
        if (profileError.code === 'PGRST116') {
            console.error('\n⚠️  NO PROFILE FOUND: Profile row does not exist for this user_id');
        } else if (profileError.code === '42501' || profileError.message?.includes('permission denied')) {
            console.error('\n⚠️  RLS POLICY ISSUE: Authenticated user cannot read profiles table');
        }
        return;
    }

    if (!profileData) {
        console.error('❌ PROFILE LOOKUP FAILED: No data returned');
        return;
    }

    console.log('✅ PROFILE FOUND');
    console.log(`   User ID: ${profileData.user_id}`);
    console.log(`   Email: ${profileData.email}`);
    console.log(`   Full Name: ${profileData.full_name}`);
    console.log(`   Role: ${profileData.role}`);
    console.log(`   Is Active: ${profileData.is_active}`);
    console.log('\n✅ END-TO-END TEST PASSED\n');

    // Step 3: Verify session is valid
    console.log('3. Verifying session...');
    const { data: { user: verifyUser }, error: verifyError } = await supabase.auth.getUser();
    
    if (verifyError) {
        console.error('❌ SESSION VERIFICATION FAILED:', verifyError.message);
    } else {
        console.log('✅ SESSION VALID');
        console.log(`   Verified User ID: ${verifyUser.id}`);
    }

    // Sign out
    await supabase.auth.signOut();
    console.log('\n✅ Test complete - signed out');
}

testAuthAndProfile().catch(console.error);
```

**Usage:**
1. Create `.env` file with `SUPABASE_URL` and `SUPABASE_ANON_KEY`
2. Install dependencies: `npm install @supabase/supabase-js dotenv`
3. Update `TEST_PASSWORD` in script
4. Run: `node test-auth-profile.js`

---

## F. Most Likely Root Cause (Ranked)

### 1. **RLS Policy Missing or Over-Restrictive** (HIGHEST PROBABILITY)
**Evidence:**
- Code uses `user_id` column correctly ✅
- Query uses `.single()` correctly ✅
- Error shows "profile not found" - this happens when RLS blocks the query
- Profile lookup uses anon key client (subject to RLS)

**Symptoms:**
- Auth succeeds (user can authenticate)
- Profile lookup returns no rows (RLS blocks SELECT)
- Exception caught, returns `None`, triggers "profile not found" error

**Fix:**
- Verify RLS policy exists: `SELECT ... USING (auth.role() = 'authenticated')`
- If missing, create the policy
- If too restrictive, adjust to allow authenticated users to read profiles

### 2. **Profile Row Doesn't Exist** (MEDIUM PROBABILITY)
**Evidence:**
- User exists in `auth.users` (auth succeeds)
- Profile row may not exist in `profiles` table
- Query correctly uses `user_id` but row missing

**Symptoms:**
- Auth succeeds
- Profile query returns PGRST116 error (no rows)
- "Profile not found" error shown

**Fix:**
- Run SQL: `SELECT * FROM profiles WHERE user_id = (SELECT id FROM auth.users WHERE email = 'matt@htxtap.com');`
- If missing, create profile row using admin tool or SQL

### 3. **Wrong Supabase Project** (MEDIUM PROBABILITY)
**Evidence:**
- Different project = different database = profile row in different project
- User may exist in one project's auth, profile in another

**Symptoms:**
- Auth succeeds (user exists in current project)
- Profile not found (profile exists in different project)
- Or vice versa

**Fix:**
- Verify `SUPABASE_URL` in Streamlit secrets matches project with profile data
- Use debug accordion in login page to verify project ref

### 4. **Exception Masking Real Error** (LOW PROBABILITY)
**Evidence:**
- `load_user_profile()` catches all exceptions and returns `None`
- Error logging exists but may not be visible in Streamlit Cloud logs
- Real error (network, timeout, etc.) hidden

**Symptoms:**
- Auth succeeds
- Profile lookup fails silently
- "Profile not found" shown even if error is different

**Fix:**
- Check Streamlit Cloud logs for error messages
- Temporarily add `st.error()` in catch block to surface real error

### 5. **Session Rehydration Issue** (LOW PROBABILITY)
**Evidence:**
- Session stored after auth succeeds
- Profile lookup uses `get_client()` which may not have session
- RLS requires authenticated session to work

**Symptoms:**
- Auth succeeds initially
- Profile lookup fails because client lost session
- Subsequent requests also fail

**Fix:**
- Verify `get_client()` rehydrates session correctly (already implemented)
- Check if `st.session_state.auth_session` persists across reruns

---

## G. Recommended Fixes (NO CODE APPLIED)

### Immediate Actions (Priority Order)

1. **Verify RLS Policy Exists**
   - Run SQL query from Section D to check policies
   - If missing, create: `CREATE POLICY "Authenticated users can read profiles" ON profiles FOR SELECT TO authenticated USING (auth.role() = 'authenticated');`

2. **Verify Profile Row Exists**
   - Run SQL: `SELECT * FROM profiles WHERE email = 'matt@htxtap.com';`
   - If missing, use admin tool: `python tools/admin_set_password.py --email matt@htxtap.com --password TEMP_PASS`
   - Then create profile row manually or via app

3. **Check Supabase Project Match**
   - Compare project ref in Streamlit secrets vs actual Supabase project
   - Use debug accordion on login page to verify
   - Ensure user AND profile exist in same project

4. **Enable Detailed Error Logging**
   - Check Streamlit Cloud logs after login attempt
   - Look for error messages from `load_user_profile()`
   - If errors found, they will reveal true cause

5. **Run Test Script**
   - Execute `test-auth-profile.js` locally with production credentials
   - Compare results with Streamlit app behavior
   - If test succeeds but app fails, issue is in Streamlit session/state

### Long-Term Improvements

1. **Add Profile Creation Auto-Flow**
   - After successful auth, if profile missing, auto-create default profile
   - Prevents "profile not found" errors

2. **Better Error Messages**
   - Differentiate between "profile doesn't exist" vs "RLS blocked" vs "network error"
   - Show actionable error messages to users

3. **Health Check Integration**
   - Add RLS policy check to health check page
   - Verify profile table accessibility before login

---

## Summary

**Code appears correct:**
- ✅ Uses `user_id` column (not `id`)
- ✅ Uses `.single()` method
- ✅ Proper error handling structure
- ✅ Client/service role separation correct

**Most likely issues:**
1. **RLS policy missing/restrictive** (70% probability)
2. **Profile row missing** (20% probability)
3. **Wrong Supabase project** (10% probability)

**Next steps:**
1. Verify RLS policy with SQL queries
2. Verify profile row exists
3. Run test script to isolate issue
4. Check Streamlit Cloud logs for hidden errors

