# Deployment Status

## Current Issue
The auth persistence fix is on branch `claude/fix-login-persistence-XFL1l` but Streamlit Cloud is deploying from `main` branch.

## To Deploy the Fix

**Option 1: Merge to Main (Recommended)**
```bash
# Switch to main branch
git checkout main

# Merge our fix branch
git merge claude/fix-login-persistence-XFL1l

# Push to trigger deployment
git push origin main
```

**Option 2: Configure Streamlit Cloud**
1. Go to https://share.streamlit.io/
2. Find your app settings
3. Change deployment branch from `main` to `claude/fix-login-persistence-XFL1l`
4. Redeploy

## Verification After Deployment
1. Log in to the app
2. Open browser console (F12)
3. Check localStorage: `localStorage.getItem("auditops_at")`
4. Press F5 to refresh
5. User should stay logged in

## Current Branch Status
- `main`: Does NOT have auth persistence fix
- `claude/fix-login-persistence-XFL1l`: Has the fix (commit 8f798eb)
