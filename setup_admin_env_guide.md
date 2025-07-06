# Admin User Environment Variable Setup Guide

## Overview
The TrendWise admin system now uses environment variables for secure configuration of admin user credentials. This eliminates hardcoded credentials and provides better security.

## Required Environment Variables

### Primary Admin User (Traditional Login)
```bash
# Required - Admin user email
ADMIN_EMAIL=your_admin@domain.com

# Required - Admin user password  
ADMIN_PASSWORD=your_secure_password

# Optional - Customize admin user details
ADMIN_USERNAME=admin
ADMIN_FIRST_NAME=Admin
ADMIN_LAST_NAME=User
```

### Optional Session-Based Admin
```bash
# Optional - For temporary admin access via /admin/admin-login
ADMIN_SESSION_PASSWORD=temporary_admin_password
```

## Setup in Coolify

1. **Go to your Coolify deployment**
2. **Navigate to Environment Variables section**
3. **Add the following variables:**
   ```
   ADMIN_EMAIL = your_admin@domain.com
   ADMIN_PASSWORD = your_secure_password
   ```
4. **Save and redeploy your application**

## How It Works

### Admin User Creation
- On application startup, the system checks for `ADMIN_EMAIL` and `ADMIN_PASSWORD`
- If both are set, it creates/updates an admin user with these credentials
- If an admin user already exists with the same email, it updates the password
- The user gets full admin privileges (`is_admin=True`, `role=admin`)

### Login Process
1. **Go to `/auth/login`** (regular login page)
2. **Enter your configured admin email and password**
3. **You'll be logged in as admin with full access**

## Security Benefits

- ✅ No hardcoded credentials in source code
- ✅ Easy to change passwords via environment variables
- ✅ Secure credential management
- ✅ Standard Flask-Login authentication flow
- ✅ Automatic admin user creation/updates

## Monitoring

Visit `/admin/admin-status` to check:
- Configuration status
- Whether admin email/password are set
- Current authentication status

## Migration from Old System

If you previously had the hardcoded admin user (`admin@cfa187260.com`):

1. **Set your new environment variables**
2. **The old admin user will continue to work until you remove it**
3. **Test the new admin user login**
4. **Optionally remove the old admin user** (use the `disable_old_admin_user.py` script)

## Example Configuration

```bash
# In your Coolify environment variables
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=SuperSecurePassword123!
ADMIN_USERNAME=admin
ADMIN_FIRST_NAME=System
ADMIN_LAST_NAME=Administrator
```

## Troubleshooting

### Admin User Not Created
- Check that both `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set
- Check application logs for error messages
- Verify environment variables are properly configured in Coolify

### Cannot Login
- Verify email/password match your environment variables exactly
- Check application logs for authentication errors
- Ensure the admin user was created (check `/admin/admin-status`)

### Environment Variables Not Working
- Restart your application after setting environment variables
- Verify variables are set correctly in Coolify
- Check for typos in variable names

## Next Steps

1. **Set your environment variables in Coolify**
2. **Redeploy your application**
3. **Test login at `/auth/login`**
4. **Check status at `/admin/admin-status`**
5. **Remove old hardcoded admin user if desired** 