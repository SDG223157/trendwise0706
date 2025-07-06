#!/usr/bin/env python3
"""
Script to manage the old admin user account
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def manage_old_admin_user():
    """Manage the old admin user account"""
    print("=" * 60)
    print("Old Admin User Management")
    print("=" * 60)
    print()
    print("Your old admin user 'admin@cfa187260.com' is still active.")
    print("Here are your options:")
    print()
    print("1. Keep both systems (recommended)")
    print("   - Keep old admin user as backup")
    print("   - Use new admin password system as primary")
    print()
    print("2. Remove admin privileges from old user")
    print("   - User account remains but loses admin access")
    print("   - Can only access via admin password")
    print()
    print("3. Delete the old admin user")
    print("   - Completely removes the user account")
    print("   - Can only access via admin password")
    print()
    print("4. Change old admin user password")
    print("   - Keep admin privileges but change password")
    print("   - Use new password for user-based admin access")
    print()
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == "1":
        print("\n✅ Keeping both systems - no changes needed!")
        print("Benefits:")
        print("- Backup admin access if environment variables fail")
        print("- Flexibility to use either authentication method")
        print("- Easy transition between old and new systems")
        
    elif choice == "2":
        print("\n🔧 To remove admin privileges from old user:")
        print("Run this in your application:")
        print()
        print("```python")
        print("from app.models import User")
        print("from app import db")
        print()
        print("# Find and update the old admin user")
        print("old_admin = User.query.filter_by(email='admin@cfa187260.com').first()")
        print("if old_admin:")
        print("    old_admin.is_admin = False")
        print("    old_admin.role = 'user'")
        print("    db.session.commit()")
        print("    print('Admin privileges removed from old user')")
        print("```")
        
    elif choice == "3":
        print("\n🗑️ To delete the old admin user:")
        print("Run this in your application:")
        print()
        print("```python")
        print("from app.models import User")
        print("from app import db")
        print()
        print("# Find and delete the old admin user")
        print("old_admin = User.query.filter_by(email='admin@cfa187260.com').first()")
        print("if old_admin:")
        print("    db.session.delete(old_admin)")
        print("    db.session.commit()")
        print("    print('Old admin user deleted')")
        print("```")
        
    elif choice == "4":
        new_password = input("\nEnter new password for old admin user: ")
        print("\n🔑 To change the old admin user password:")
        print("Run this in your application:")
        print()
        print("```python")
        print("from app.models import User")
        print("from app import db")
        print()
        print("# Find and update password for old admin user")
        print("old_admin = User.query.filter_by(email='admin@cfa187260.com').first()")
        print("if old_admin:")
        print(f"    old_admin.set_password('{new_password}')")
        print("    db.session.commit()")
        print("    print('Password updated for old admin user')")
        print("```")
        
    else:
        print("\n❌ Invalid choice. Please run the script again.")
        return
    
    print("\n" + "=" * 60)
    print("SECURITY RECOMMENDATIONS")
    print("=" * 60)
    print("• Always ensure you have at least one way to access admin features")
    print("• Test admin password system before removing user-based access")
    print("• Keep environment variables secure and backed up")
    print("• Consider keeping the old admin user as emergency backup")
    print()

if __name__ == "__main__":
    try:
        manage_old_admin_user()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 