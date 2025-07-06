# app/utils/admin_auth.py

import os
from flask import session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import logging
from app.models import User
from app import db

logger = logging.getLogger(__name__)

class AdminAuth:
    """Admin password authentication utility"""
    
    @staticmethod
    def verify_admin_password(password: str) -> bool:
        """
        Verify if the provided password matches the admin password
        
        Args:
            password: The password to verify
            
        Returns:
            bool: True if password is correct, False otherwise
        """
        try:
            # Check if session-based admin password is configured (separate from user admin password)
            admin_session_password = current_app.config.get('ADMIN_SESSION_PASSWORD')
            admin_session_password_hash = current_app.config.get('ADMIN_SESSION_PASSWORD_HASH')
            
            if admin_session_password:
                # Use plain text comparison for environment variable (less secure but simpler)
                return password == admin_session_password
            elif admin_session_password_hash:
                # Use hash comparison (more secure)
                return check_password_hash(admin_session_password_hash, password)
            else:
                logger.warning("No session admin password configured in environment variables")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying admin password: {str(e)}")
            return False
    
    @staticmethod
    def generate_admin_password_hash(password: str) -> str:
        """
        Generate a hash for admin password
        
        Args:
            password: The password to hash
            
        Returns:
            str: The hashed password
        """
        return generate_password_hash(password)
    
    @staticmethod
    def grant_session_admin_privileges():
        """Grant admin privileges for the current session"""
        session['admin_authenticated'] = True
        session['admin_auth_time'] = datetime.now().isoformat()
        session.permanent = True
        logger.info("Admin privileges granted for session")
    
    @staticmethod
    def revoke_session_admin_privileges():
        """Revoke admin privileges for the current session"""
        session.pop('admin_authenticated', None)
        session.pop('admin_auth_time', None)
        logger.info("Admin privileges revoked for session")
    
    @staticmethod
    def has_session_admin_privileges() -> bool:
        """Check if current session has admin privileges"""
        try:
            if not session.get('admin_authenticated'):
                return False
            
            # Check if admin session has expired (optional - 8 hours)
            auth_time_str = session.get('admin_auth_time')
            if auth_time_str:
                auth_time = datetime.fromisoformat(auth_time_str)
                if datetime.now() - auth_time > timedelta(hours=8):
                    AdminAuth.revoke_session_admin_privileges()
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking session admin privileges: {str(e)}")
            return False
    
    @staticmethod
    def grant_user_admin_privileges(user_id: int) -> bool:
        """
        Grant permanent admin privileges to a user account
        
        Args:
            user_id: The user ID to grant admin privileges to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return False
            
            user.is_admin = True
            user.role = 'admin'
            db.session.commit()
            
            logger.info(f"Admin privileges granted to user: {user.username} ({user.email})")
            return True
            
        except Exception as e:
            logger.error(f"Error granting admin privileges to user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def revoke_user_admin_privileges(user_id: int) -> bool:
        """
        Revoke admin privileges from a user account
        
        Args:
            user_id: The user ID to revoke admin privileges from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return False
            
            user.is_admin = False
            user.role = 'user'
            db.session.commit()
            
            logger.info(f"Admin privileges revoked from user: {user.username} ({user.email})")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking admin privileges from user {user_id}: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_admin_config_info() -> dict:
        """Get information about admin configuration"""
        return {
            # User-based admin configuration
            'admin_user_email_configured': bool(current_app.config.get('ADMIN_EMAIL')),
            'admin_user_password_configured': bool(current_app.config.get('ADMIN_PASSWORD')),
            
            # Session-based admin configuration
            'admin_session_password_configured': bool(current_app.config.get('ADMIN_SESSION_PASSWORD')),
            'admin_session_password_hash_configured': bool(current_app.config.get('ADMIN_SESSION_PASSWORD_HASH')),
            
            # Session status
            'session_admin_active': AdminAuth.has_session_admin_privileges(),
            'auth_time': session.get('admin_auth_time')
        } 