# AuditOps - Streamlit Operations Portal

A comprehensive operations portal for auditors, administrators, and managers built with Streamlit and Supabase. This internal employee and client operations system provides role-based access control, time tracking, pay period management, approvals, and client data access.

## ⚠️ IMPORTANT: Production Structure

**Streamlit Cloud runs from the NESTED directory:** `auditops-streamlit/`

**All production code lives in:**
- `auditops-streamlit/app.py` - Main entrypoint (DO NOT edit root `app.py`)
- `auditops-streamlit/src/` - Source code (DO NOT edit root `src/`)
- `auditops-streamlit/pages/` - Streamlit pages (DO NOT edit root `pages/`)
- `auditops-streamlit/requirements.txt` - Dependencies (DO NOT edit root `requirements.txt`)

**Root-level files (`app.py`, `src/`, `pages/`, `requirements.txt`) are archived in `archive_root_app/` and are NOT used by production.**

**See `DEPLOYMENT_ALIGNMENT_REPORT.md` for complete details on the deployment structure.**

## Features

- **Authentication**: Secure login using Supabase Auth (email + password)
- **Role-Based Access Control**: Three roles (ADMIN, MANAGER, AUDITOR) with appropriate permissions
- **Time Tracking**: Shift check-in/check-out functionality for auditors
- **Pay Period Management**: Create, lock, and export pay period summaries
- **Approvals Workflow**: Managers and admins can approve/reject submitted shifts
- **Client Management**: Admin interface for managing client profiles
- **Access Logging**: Track access to protected documents and sensitive data
- **Health Monitoring**: System health check page for connectivity and configuration

## Prerequisites

- Python 3.8 or higher
- A Supabase project (free tier works)
- Streamlit Cloud account (for deployment) or local Streamlit installation

## Setup Instructions

### 1. Clone or Download the Repository

```bash
cd C:\Users\matt\auditops-streamlit
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** in your Supabase dashboard
3. Run the SQL script from `sql/schema.sql` to create all tables, indexes, and RLS policies
4. Create a storage bucket (optional, for file uploads):
   - Go to **Storage** in Supabase dashboard
   - Create a new bucket (e.g., `client-docs`)
   - Set appropriate policies

### 4. Create User Profiles

After running the schema, you need to link Supabase Auth users to profiles:

1. Create users in Supabase Auth (Authentication > Users > Add User)
2. Note the user's UUID from Auth
3. Insert a profile record in the `profiles` table:

```sql
INSERT INTO profiles (id, email, full_name, role)
VALUES ('<user-uuid-from-auth>', 'admin@example.com', 'Admin User', 'ADMIN');
```

Repeat for all users (ADMIN, MANAGER, AUDITOR roles).

### 5. Configure Secrets

#### For Local Development

Create a `.streamlit/secrets.toml` file in the project root:

```toml
[supabase]
url = "https://your-project.supabase.co"
anon_key = "your-anon-key-here"
service_role_key = "your-service-role-key-here"
jwt_secret = "your-jwt-secret-here"  # Optional, for advanced token verification
```

**Where to find these values:**
- **URL**: Project Settings > API > Project URL
- **anon_key**: Project Settings > API > Project API keys > `anon` `public`
- **service_role_key**: Project Settings > API > Project API keys > `service_role` `secret` (keep this secure!)
- **jwt_secret**: Project Settings > API > JWT Secret

#### For Streamlit Cloud Deployment

1. Go to your Streamlit Cloud app settings
2. Click **Secrets**
3. Add the same `secrets.toml` content as above

**Important**: Never commit `secrets.toml` to version control. It's already in `.gitignore`.

### 6. Run Locally

**For Production (Streamlit Cloud):**
```bash
cd auditops-streamlit
streamlit run app.py
```

**Note:** If you have root-level files, they are archived and not used. Always run from `auditops-streamlit/` directory.

The app will open in your browser at `http://localhost:8501`

### 7. Deploy to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app**
4. Connect your GitHub repository
5. **Set the main file path to `auditops-streamlit/app.py`** (NOT root `app.py`)
6. Add your secrets in the app settings (see step 5)
7. Deploy!

**Important:** Streamlit Cloud must be configured to use `auditops-streamlit/app.py` as the entrypoint.

## Project Structure

```
auditops-streamlit/                 # ⚠️ PRODUCTION CODE (Streamlit Cloud runs from here)
├── app.py                          # Main application entry point (PRODUCTION)
├── pages/                          # Streamlit multi-page app pages (PRODUCTION)
│   ├── 00_Reset_Password.py        # Password reset page
│   ├── 01_Auditor_Field_Mode.py   # Auditor: Check in/out
│   ├── 02_Auditor_My_Pay.py       # Auditor: View pay history
│   ├── 10_Admin_Approvals.py      # Manager/Admin: Approve shifts
│   ├── 11_Admin_Pay_Periods.py    # Admin: Manage pay periods
│   ├── 12_Admin_Clients.py        # Admin: Manage clients
│   ├── 13_Admin_Secrets_Access_Log.py  # Admin: View access logs
│   └── 99_Admin_Health_Check.py   # Admin: System health
├── src/                            # Source modules (PRODUCTION)
│   ├── __init__.py
│   ├── config.py                   # Configuration and secrets
│   ├── supabase_client.py         # Supabase client initialization
│   ├── auth.py                     # Authentication helpers
│   ├── db.py                       # Database CRUD operations
│   ├── storage.py                  # File storage helpers
│   ├── utils.py                    # Utility functions
│   └── pdf_statements.py           # PDF generation
├── requirements.txt                # Python dependencies (PRODUCTION)
├── sql/
│   └── schema.sql                  # Database schema
├── archive_root_app/               # ⚠️ ARCHIVED (NOT USED IN PRODUCTION)
│   ├── app.py                      # Old root entrypoint (archived)
│   ├── src/                        # Old root source (archived)
│   ├── pages/                      # Old root pages (archived)
│   └── requirements.txt           # Old root deps (archived)
├── DEPLOYMENT_ALIGNMENT_REPORT.md  # Deployment structure documentation
├── DRIFT_SYNC_REPORT.md            # Root vs nested comparison report
└── README.md                       # This file
```

**⚠️ CRITICAL:** Always edit files in `auditops-streamlit/` for production changes. Root-level files are archived and ignored by Streamlit Cloud.

## Role Permissions

### AUDITOR
- View own profile
- Check in/out for shifts
- Submit shifts for approval
- View own pay history and download statements

### MANAGER
- All auditor permissions
- Approve/reject submitted shifts
- View client list (read-only)

### ADMIN
- All manager permissions
- Manage clients (create, update, delete)
- Manage pay periods (create, lock, export)
- View access logs
- Run health checks
- Full system access

## Database Schema

The application uses the following main tables:

- **profiles**: User profiles linked to Supabase Auth
- **clients**: Client information
- **shifts**: Time tracking entries (check-in/check-out)
- **pay_periods**: Pay period definitions
- **pay_items**: Calculated pay items for each period
- **approvals**: Approval decisions for shifts
- **access_logs**: Audit trail for document access

See `sql/schema.sql` for the complete schema with indexes and RLS policies.

## Security Notes

1. **Never commit secrets**: The `.streamlit/secrets.toml` file should never be committed to version control.
2. **Service Role Key**: Only use the service role key for admin operations. The app uses the anon key for regular operations.
3. **RLS Policies**: Row Level Security policies are defined in the schema. Review and adjust based on your security requirements.
4. **Access Logging**: All access to protected documents is logged in the `access_logs` table.

## Troubleshooting

### "SUPABASE_URL is required" Error
- Ensure your `.streamlit/secrets.toml` file exists and contains the `[supabase]` section
- Check that environment variables are set if not using secrets.toml

### "User profile not found" Error
- Make sure you've created a profile record in the `profiles` table linked to your Supabase Auth user ID
- Verify the user exists in Supabase Auth

### Database Connection Issues
- Verify your Supabase URL and keys are correct
- Check that the schema has been run in your Supabase SQL Editor
- Use the Health Check page to diagnose connectivity issues

### Role-Based Access Not Working
- Ensure the user's profile has the correct `role` value (ADMIN, MANAGER, or AUDITOR)
- Check that RLS policies allow the user to access the required tables

## Development Notes

- The app uses UTC timestamps for all datetime operations
- UUIDs are used for all primary keys
- The codebase is structured to support future enhancements (e.g., more granular permissions, additional approval workflows)
- PDF generation uses ReportLab and can be extended for more complex statements

## License

This is an internal operations system. Use as needed for your organization.

## Support

For issues or questions, contact your system administrator or review the Health Check page for system status.

