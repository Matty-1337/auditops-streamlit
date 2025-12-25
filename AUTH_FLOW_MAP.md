# End-to-End Authentication Flow Map

## File Locations & Line Numbers

### 1. SUPABASE CLIENT CREATION

**File**: `src/supabase_client.py`
- **Line 12-38**: `get_client(service_role=False)` - Creates/returns Supabase client
- **Line 27**: Gets URL from `get_supabase_url()`
- **Line 36-37**: Creates client with anon key (for auth operations)
- **Line 31-32**: Creates client with service_role key (for admin operations)
- **Global instances**: `_supabase_client`, `_supabase_service_client` (lines 8-9)
- **Issue**: Client instances are global and NOT rehydrated with session on rerun

**File**: `src/config.py`
- **Line 29-34**: `get_supabase_url()` - Reads from secrets/env
- **Line 37-57**: `get_supabase_key(service_role=False)` - Reads anon/service key

### 2. LOGIN UI TRIGGERS

**File**: `app.py`
- **Line 112-136**: `show_login_page()` - Email/password form
- **Line 119-132**: Form submission → calls `login(email, password)`
- **Line 23-36**: CSS styling (not auth-related)

**File**: `src/auth.py`
- **Line 10-54**: `login(email, password)` - Password authentication
- **Line 22**: Gets client via `get_client(service_role=False)`
- **Line 23-26**: Calls `client.auth.sign_in_with_password()`
- **Line 30-31**: Stores in `st.session_state.auth_user` and `auth_session`
- **Line 34**: Loads profile via `load_user_profile()`

**MAGIC LINK TRIGGER**: Not in codebase - triggered externally via Supabase email

### 3. CALLBACK HANDLING (TOKEN EXTRACTION)

**File**: `app.py`
- **Line 39-76**: JavaScript injection via `st.markdown(unsafe_allow_html=True)`
  - **Line 46-47**: Checks for hash fragment and query params
  - **Line 49-71**: Converts `#access_token=...` → `?access_token=...`
  - **Line 68-70**: Uses `window.history.replaceState()` + `window.location.reload()`
  - **CRITICAL**: This runs AFTER page load, may not execute before auth gate

- **Line 187-191**: Python query param reading
  - **Line 187**: `query_params = st.query_params`
  - **Line 188-189**: Extracts `access_token`, `refresh_token`
  - **Line 190**: Extracts `type` (magiclink/recovery)
  - **Line 191**: Extracts `code` (PKCE flow)

**File**: `src/auth.py`
- **Line 169-242**: `authenticate_with_tokens(access_token, refresh_token)`
  - **Line 181**: Gets client (NEW instance if global was cleared)
  - **Line 187**: Calls `client.auth.set_session(access_token, refresh_token)`
  - **Line 201-213**: Stores in `st.session_state`
  - **Line 216**: Loads profile

### 4. SESSION PERSISTENCE

**Storage Mechanism**: `st.session_state` (Streamlit session state)
- **Keys**:
  - `auth_user` (line 30, 203 in `src/auth.py`)
  - `auth_session` (line 31, 205 in `src/auth.py`)
  - `user_profile` (line 36, 218 in `src/auth.py`)

**Persistence Scope**: Per-browser session (cleared on browser close/refresh unless preserved)

**CRITICAL ISSUE**: 
- Supabase client instances (`_supabase_client`) are global Python variables
- They are NOT automatically rehydrated with session from `st.session_state`
- After `set_session()`, the client has the session internally
- But on next rerun, if a NEW client is created, it has NO session
- The code stores session in `st.session_state` but doesn't rehydrate the client

**File**: `src/supabase_client.py`
- **Line 35-38**: Creates client ONCE, reuses global instance
- **Line 8**: `_supabase_client: Client | None = None` - Global, not per-request
- **Issue**: If client is recreated or module reloaded, session is lost

### 5. "LOGGED-IN GATE" LOGIC

**File**: `app.py`
- **Line 234-238**: Main gate in `main()`
  - **Line 235**: `if not is_authenticated():`
  - **Line 236**: Shows login page
  - **Line 237**: Else shows main app

**File**: `src/auth.py`
- **Line 81-83**: `is_authenticated()` - Checks `st.session_state.auth_user`
- **Line 71-73**: `get_current_user()` - Returns `st.session_state.get("auth_user")`
- **Line 76-78**: `get_current_profile()` - Returns `st.session_state.get("user_profile")`

**Gate Logic**: 
- ✅ Checks `st.session_state.auth_user` exists
- ❌ Does NOT verify session is valid with Supabase
- ❌ Does NOT rehydrate Supabase client with stored session

### 6. RERUN & QUERY PARAM CLEARING

**File**: `app.py`
- **Line 206-207**: Clears query params AFTER successful PKCE auth
- **Line 227-228**: Clears query params AFTER successful token auth
- **Line 104**: Clears query params AFTER password reset
- **Line 132, 145, 160**: Various `st.rerun()` calls

**Timing Issue**: 
- Query params cleared BEFORE verifying session persists
- If rerun happens and client loses session, user appears logged out

### 7. PASSWORD RESET FLOW

**File**: `app.py`
- **Line 79-109**: `show_recovery_page(access_token, refresh_token)`
- **Line 101**: Calls `reset_password(new_password, access_token, refresh_token)`

**File**: `src/auth.py`
- **Line 245-303**: `reset_password()`
- **Line 264**: Sets session with tokens
- **Line 279**: Updates password
- **Line 283-285**: Stores session in `st.session_state`

---

## CRITICAL FLOW ISSUES IDENTIFIED

### Issue A: JavaScript Execution Timing
- JavaScript (line 39-76) runs via `st.markdown()` with `unsafe_allow_html=True`
- This may execute AFTER the Python code has already checked query params
- Streamlit renders Python first, then JavaScript
- If hash exists but JS hasn't converted it yet, Python sees no tokens

### Issue B: Session Not Rehydrated
- `set_session()` stores session in Supabase client instance
- Session also stored in `st.session_state`
- But on rerun, if client is recreated, it has NO session
- Code never calls `client.auth.set_session()` again with stored tokens
- Gate only checks `st.session_state.auth_user`, not actual Supabase session

### Issue C: Client Instance Lifecycle
- Global client instances may be cleared/recreated between reruns
- No mechanism to rehydrate client with stored session tokens
- `get_client()` returns existing global OR creates new one
- New client = no session, even if tokens exist in `st.session_state`

### Issue D: Query Param Clearing Too Early
- Query params cleared immediately after `set_session()`
- But if rerun happens and client loses session, tokens are gone
- No way to recover from failed session persistence

---

## EXACT CODE PATHS FOR MAGIC LINK FLOW

1. **User clicks magic link** → Supabase redirects to:
   `https://auditops.streamlit.app#access_token=xxx&refresh_token=yyy&type=magiclink`

2. **Browser loads page** → Streamlit server starts Python execution

3. **Python executes** (`app.py:169-242`):
   - Line 187: Reads `st.query_params` → **NO TOKENS YET** (still in fragment)
   - Line 235: Checks `is_authenticated()` → False
   - Line 236: Shows login page

4. **JavaScript executes** (`app.py:41-75`):
   - Line 49: Detects hash fragment
   - Line 68-70: Converts to query params and reloads

5. **Page reloads** → Python executes again:
   - Line 187: Now sees query params
   - Line 216: Calls `authenticate_with_tokens()`
   - Line 187: `set_session()` succeeds
   - Line 203: Stores in `st.session_state`
   - Line 227: Clears query params
   - Line 228: `st.rerun()`

6. **Rerun happens**:
   - Line 235: Checks `is_authenticated()` → True (from `st.session_state`)
   - Line 237: Shows main app ✅

**BUT**: If client instance is lost/recreated, session is gone from Supabase client
**AND**: Code never rehydrates client with tokens from `st.session_state`

