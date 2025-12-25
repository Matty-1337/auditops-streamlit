# Password Recovery & Reset Flow

Complete guide for using and configuring the password recovery and reset functionality in AuditOps.

## How to Use Forgot Password

1. **From Login Page**:
   - On the login screen, click the **"Forgot Password?"** button below the login form
   - Enter your email address
   - Click **"Send Reset Link"**
   - You will see a confirmation message (even if the email doesn't exist, for security)

2. **Check Your Email**:
   - Open your email inbox
   - Look for a password reset email from Supabase
   - Click the reset link in the email

3. **Reset Your Password**:
   - You will be redirected to the Reset Password page
   - Enter your new password (minimum 6 characters)
   - Confirm your new password
   - Click **"Reset Password"**
   - You will be automatically logged out and redirected to the login page

4. **Login with New Password**:
   - Go back to the login page
   - Enter your email and new password
   - Click **"Login"**

## Supabase Dashboard Configuration

### Required Settings

**Path**: Supabase Dashboard → Your Project → Authentication → URL Configuration

1. **Site URL**:
   - **Value**: `https://auditops.streamlit.app`
   - **Purpose**: Base URL where Supabase redirects users after password reset
   - **How to Set**:
     - Go to: Authentication → URL Configuration
     - Find "Site URL" field
     - Enter: `https://auditops.streamlit.app`
     - Click "Save"

2. **Redirect URLs** (Additional Redirect URLs section):
   - **Value**: `https://auditops.streamlit.app/*`
   - **Purpose**: Allows Supabase to redirect to any path in your Streamlit app
   - **How to Set**:
     - In the same URL Configuration page
     - Scroll to "Additional Redirect URLs" section
     - Click "Add URL" or "+" button
     - Enter: `https://auditops.streamlit.app/*`
     - Click "Save" or checkmark

### Visual Guide

```
Supabase Dashboard
  └─ Your Project
      └─ Authentication (left sidebar)
          └─ URL Configuration
              ├─ Site URL: [https://auditops.streamlit.app        ]
              └─ Additional Redirect URLs:
                  └─ [https://auditops.streamlit.app/*]  [+ Add URL]
```

### Important Notes

- **Wildcard (`*`)**: The `/*` allows redirects to any path, which is necessary because Streamlit uses query parameters for recovery tokens
- **No Trailing Slash**: Use `https://auditops.streamlit.app` (not `https://auditops.streamlit.app/`)
- **HTTPS Required**: Use `https://` not `http://`
- **Remove Localhost URLs**: If you see any `localhost` URLs in Redirect URLs, remove them for production

## Verification Steps

### Step 1: Trigger Forgot Password

1. Go to the login page: `https://auditops.streamlit.app`
2. Click **"Forgot Password?"** button
3. Enter your email address (e.g., `matt@htxtap.com`)
4. Click **"Send Reset Link"**
5. ✅ **Expected**: See message: "If that email address exists, a password reset link has been sent..."

### Step 2: Click Email Link

1. Open your email inbox
2. Find the password reset email from Supabase
3. Click the reset link in the email
4. ✅ **Expected**: 
   - Browser opens: `https://auditops.streamlit.app`
   - You are redirected to the Reset Password page
   - Password reset form appears

### Step 3: Set New Password

1. On the Reset Password page, enter a new password (minimum 6 characters)
2. Confirm the new password
3. Click **"Reset Password"**
4. ✅ **Expected**: 
   - Success message: "✅ Password reset successfully!"
   - You are automatically logged out
   - Redirected back to login page

### Step 4: Login with New Password

1. On the login page, enter your email address
2. Enter your **new password** (the one you just set)
3. Click **"Login"**
4. ✅ **Expected**: Successfully logged in and redirected to main app

## Troubleshooting

### Issue: "Forgot Password?" button not showing

**Solution**: 
- Check that Streamlit Cloud has finished deploying the latest code
- Hard refresh the browser (Ctrl+F5 or Cmd+Shift+R)
- Check browser console for JavaScript errors

### Issue: Reset link doesn't work / Redirects to wrong page

**Solution**:
- Verify Supabase Dashboard → Authentication → URL Configuration:
  - Site URL is: `https://auditops.streamlit.app`
  - Redirect URLs includes: `https://auditops.streamlit.app/*`
- Check browser URL - should contain `#access_token=...&refresh_token=...&type=recovery`
- JavaScript should convert fragment to query params automatically

### Issue: "Invalid or expired password reset link"

**Solution**:
- Password reset links expire after a period (typically 1 hour)
- Request a new reset link from the login page
- Verify the link wasn't used already (links are single-use)

### Issue: Email not received

**Solution**:
- Check spam/junk folder
- Verify email address is correct
- Check Supabase project email configuration (SMTP settings)
- Wait a few minutes (email delivery can be delayed)
- Try requesting a new reset link

### Issue: Password reset succeeds but can't login

**Solution**:
- Verify you're using the **new password** (not the old one)
- Check for typos in email/password
- Try requesting a new reset link and repeating the process
- Contact administrator if issue persists

## Security Features

- **Email Enumeration Protection**: The app always shows the same success message regardless of whether the email exists
- **Token Security**: Recovery tokens are single-use and expire
- **No Password Leakage**: Passwords are never logged or displayed
- **Session Security**: Users are logged out after password reset and must log in again

## Technical Details

- **Password Reset Page**: `pages/00_Reset_Password.py`
- **Recovery Email Function**: `show_forgot_password()` in `app.py`
- **Supabase Method**: `client.auth.reset_password_for_email()`
- **Password Update Method**: `client.auth.update_user({"password": new_password})`
- **Token Handling**: JavaScript converts URL fragments to query parameters for Streamlit server access

