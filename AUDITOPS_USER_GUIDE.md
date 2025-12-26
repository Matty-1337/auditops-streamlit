# AuditOps User Guide
## Complete Step-by-Step Documentation

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Getting Started](#getting-started)
3. [Check-In Process](#check-in-process)
4. [Check-Out Process](#check-out-process)
5. [Viewing Pay Information](#viewing-pay-information)
6. [Admin Functions](#admin-functions)
7. [Troubleshooting](#troubleshooting)

---

## System Overview

**AuditOps** is a time tracking and shift management system for auditors. The system allows:
- PIN-based secure login
- Check in/out at client locations
- Access to site information and credentials
- Shift submission and approval workflow
- Pay period management
- Pay statement generation

---

## Getting Started

### First Time Setup (Administrator Required)

**Prerequisites:**
1. Administrator must create your user account in the `app_users` table
2. Your account must have:
   - `id` (automatically generated)
   - `name` (your full name)
   - `passcode` (your 4-digit PIN)
   - `role` (AUDITOR, ADMIN, or MANAGER)
   - `auth_uuid` (automatically generated UUID)

**Database Requirements:**
- Active clients must exist in the `clients` table
- Your user must be in the `app_users` table with a valid PIN

---

## Check-In Process

### What You Need Before Checking In
✅ **Active clients** must exist in the system
✅ You must be logged in with your PIN
✅ You must have AUDITOR role or higher

### Step-by-Step: How to Check In

**1. Log In to AuditOps**
- Go to the AuditOps application URL
- Enter your 4-digit PIN
- Click "Login"

**2. Navigate to Field Mode**
- Click "Auditor Field Mode" in the left sidebar
- You'll see the Field Mode page with two columns:
  - Left: Current Shift / Check In form
  - Right: Recent Shifts history

**3. Check In to a Shift**

If you see: **"No active clients available. Contact an administrator."**
- This means there are no clients in the system
- Contact your administrator to add clients first
- You cannot check in until clients exist

If clients are available:
- **Select a Client** from the dropdown menu
- **Add Notes** (optional) - Any information about the shift
- Click **"✅ Check In"** button

**4. What Happens After Check-In**
- System creates a new shift record
- Records current date/time as check-in time
- Shift status is set to "DRAFT"
- You'll see "✅ You have an active shift" message
- The check-in form is replaced with shift details

---

## During Your Shift

### Viewing Site Information & Secrets

**What Are Secrets?**
- WiFi names and passwords
- Alarm codes
- Lockbox codes
- Other site-specific information

**How to Access Secrets:**
1. While checked in, you'll see **"Site Info / Secrets"** section
2. Click **"Reveal Site Info (60s)"** button
3. Information displays for **60 seconds only**
4. After 60 seconds, information automatically hides
5. All access is logged for security

**What You'll See:**
- WiFi Name
- WiFi Password
- Alarm Code
- Lockbox Code
- Other Site Notes

**Security Features:**
- Information only visible for 60 seconds
- All views are logged with timestamp
- Can only access secrets while checked in to that client

---

## Check-Out Process

### Step-by-Step: How to Check Out

**1. Click the Check Out Button**
- While your shift is active, you'll see **"🛑 Check Out"** button
- Click this button when you're ready to end your shift

**2. What Happens During Check-Out**
- System records current date/time as check-out time
- Automatically calculates total hours worked
- Hours are added to your shift notes
- Shift remains in DRAFT status

**3. After Check-Out**
- Your shift moves to "Draft shift ready to submit"
- You'll see shift summary with:
  - Client name
  - Check-in time
  - Check-out time
  - Total hours
  - Notes

---

## Submit for Approval

### Why Submit?
- Shifts must be submitted for manager/admin approval
- Only approved shifts count toward your pay
- Submitted shifts can be reviewed and approved by managers

### How to Submit a Shift

**1. After Checking Out**
- You'll see **"📋 Draft shift ready to submit"**
- Review your shift details:
  - Client name
  - Check-in/out times
  - Hours worked
  - Notes

**2. Submit the Shift**
- Click **"📤 Submit for Approval"** button
- Status changes from DRAFT to SUBMITTED
- Shift is now visible to managers for approval

**3. What Happens Next**
- Managers see your shift in "Admin Approvals" page
- They can approve or reject it
- Approved shifts go to "My Pay" for payment

---

## Viewing Pay Information

### Navigate to "Auditor My Pay"

**1. Access Pay Page**
- Click **"Auditor My Pay"** in left sidebar
- View all your approved shifts and pay items

**2. What You Can See**
- Pay periods (weekly, biweekly, or monthly)
- Total hours worked
- Total amount owed
- Individual shift details
- Pay statements

**3. Download Pay Statements**
- Select a pay period
- Click **"Download Statement"** button
- Receive PDF with detailed breakdown

---

## Admin Functions

### Admin Approvals (Admin/Manager Only)

**Purpose:** Review and approve submitted shifts

**Steps:**
1. Go to **"Admin Approvals"** in sidebar
2. See all pending shifts
3. Review shift details
4. Click **Approve** or **Reject**
5. Add approval notes if needed

### Admin Clients (Admin Only)

**Purpose:** Manage client information

**Add New Client:**
1. Go to **"Admin Clients"** page
2. Click **"➕ Create New Client"**
3. Enter:
   - Client Name
   - Address
   - Contact Information
   - Notes
4. Click **"Create Client"**

**Edit Client:**
1. Find client in list
2. Click **"Edit"** button
3. Update information
4. Save changes

**Add Client Secrets:**
1. Find client in list
2. Click **"Manage Secrets"**
3. Enter:
   - WiFi Name & Password
   - Alarm Code
   - Lockbox Code
   - Other site notes
4. Save

### Admin Pay Periods (Admin Only)

**Purpose:** Create and manage pay periods

**Create Pay Period:**
1. Go to **"Admin Pay Periods"**
2. Click **"Create New Period"**
3. Select:
   - Start Date
   - End Date
   - Period Type (weekly/biweekly/monthly)
4. Click **"Create"**

**Lock Pay Period:**
1. Find period in list
2. Click **"Lock Period"**
3. Locked periods cannot be modified
4. Generate pay summaries for locked periods

---

## Change Your PIN

### How to Change Your PIN

**1. From Main Page**
- Log in with current PIN
- In the sidebar, find **"🔐 Change My PIN"** expander
- Click to expand

**2. Enter New PIN**
- Enter **New 4-Digit PIN**
- Enter **Confirm New PIN** (must match)
- Click **"Update PIN"**

**3. Validation**
- PIN must be exactly 4 digits
- PIN must be numbers only
- Confirmation must match new PIN
- Success message confirms change

**4. Next Login**
- Use your new PIN to log in
- Old PIN no longer works

---

## Troubleshooting

### "No active clients available"

**Problem:** Cannot check in because dropdown is empty

**Solution:**
1. Contact administrator
2. Admin must add clients to the system
3. Go to Admin Clients → Create New Client
4. At least one active client must exist

---

### "Invalid Code" when logging in

**Problem:** PIN not recognized

**Solutions:**
1. Verify you're entering correct 4-digit PIN
2. Check with administrator that your account exists
3. Confirm PIN hasn't been changed recently
4. Ensure account is active in `app_users` table

---

### "Error loading shifts" or UUID errors

**Problem:** Database compatibility issue

**Solution (Administrator):**
1. Run this SQL command:
```sql
ALTER TABLE app_users ADD COLUMN IF NOT EXISTS auth_uuid UUID DEFAULT gen_random_uuid();
UPDATE app_users SET auth_uuid = gen_random_uuid() WHERE auth_uuid IS NULL;
```
2. Ensure all user ID columns in database are BIGINT or UUID type (not mixed)
3. Verify foreign key relationships

---

### Can't see Admin pages

**Problem:** Admin pages not visible in sidebar

**Solution:**
1. Check your role in `app_users` table
2. Only ADMIN role can see admin pages
3. Contact administrator to update your role if needed
4. Log out and log back in after role change

---

### Secrets not displaying

**Problem:** "Reveal Site Info" doesn't work

**Possible Causes:**
1. Not currently checked in to a shift
2. Client doesn't have secrets configured
3. Secrets already revealed (60 second timeout)

**Solutions:**
1. Ensure you're checked in to an active shift
2. Ask admin to add secrets for the client
3. Wait and click "Reveal" again if timeout expired

---

## Database Setup Guide (Administrators)

### Required Tables

**1. app_users** (For PIN authentication)
```sql
CREATE TABLE app_users (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  passcode TEXT NOT NULL,
  role TEXT DEFAULT 'AUDITOR',
  auth_uuid UUID DEFAULT gen_random_uuid()
);
```

**2. clients** (Client information)
```sql
CREATE TABLE clients (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  address TEXT,
  contact_info TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**3. shifts** (Time tracking)
```sql
CREATE TABLE shifts (
  id SERIAL PRIMARY KEY,
  auditor_id UUID NOT NULL,
  client_id BIGINT REFERENCES clients(id),
  check_in TIMESTAMPTZ NOT NULL,
  check_out TIMESTAMPTZ,
  status TEXT DEFAULT 'draft',
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**4. client_secrets** (Secure site information)
```sql
CREATE TABLE client_secrets (
  id SERIAL PRIMARY KEY,
  client_id BIGINT REFERENCES clients(id),
  wifi_name TEXT,
  wifi_password TEXT,
  alarm_code TEXT,
  lockbox_code TEXT,
  other_site_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Initial Setup Checklist

- [ ] Create all required tables
- [ ] Add `auth_uuid` column to `app_users`
- [ ] Create at least one admin user
- [ ] Create at least one client
- [ ] Test PIN login
- [ ] Test check-in/out flow
- [ ] Configure client secrets
- [ ] Test approval workflow

---

## Support

**For Technical Issues:**
- Contact your system administrator
- Check this documentation first
- Provide error messages when reporting issues

**For Account Issues:**
- Contact administrator to reset PIN
- Verify your role permissions
- Confirm account is active

---

## Quick Reference

| Action | Page | Role Required |
|--------|------|---------------|
| Check In/Out | Auditor Field Mode | AUDITOR |
| View Pay | Auditor My Pay | AUDITOR |
| Change PIN | Main Page Sidebar | Any |
| Approve Shifts | Admin Approvals | ADMIN/MANAGER |
| Manage Clients | Admin Clients | ADMIN |
| Create Pay Periods | Admin Pay Periods | ADMIN |
| View Access Logs | Admin Secrets Access Log | ADMIN |

---

**Document Version:** 1.0
**Last Updated:** December 2025
**System:** AuditOps PIN Authentication System
