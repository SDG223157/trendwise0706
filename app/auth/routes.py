from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User
from datetime import datetime
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests as google_requests
from app.utils.activity_logger import log_user_activity
from app.utils.email_validator import is_email_domain_blocked
from app.utils.cache.user_cache import user_cache
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        # Check if email domain is blocked
        if is_email_domain_blocked(email):
            flash('Email domain not allowed for login.', 'error')
            return redirect(url_for('auth.login'))

        # TRY CACHE FIRST
        cached_user_data = user_cache.get_user_by_email(email)
        if cached_user_data:
            logger.debug(f"🎯 User cache hit for email: {email}")
            # Reconstruct user object from cached data
            user = User.query.get(cached_user_data['id'])  # Get fresh object for Flask-Login
        else:
            # FALLBACK TO DATABASE
            user = User.query.filter_by(email=email).first()
            if user:
                # Cache user data for future lookups
                user_cache.cache_user_complete(user.to_dict())
                logger.debug(f"💾 Cached user data for: {email}")

        if not user or not check_password_hash(user.password_hash, password):
            flash('Please check your email and password and try again.', 'error')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        
        # Log the login activity
        log_user_activity(user.id, 'login')
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
        flash('Logged in successfully.', 'success')
        return redirect(next_page)

    return render_template('auth/login.html', title='Login')

@bp.route('/google')
def google():
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']]
                }
            },
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
        )
        flow.redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        return redirect(authorization_url)
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        flash('Failed to initialize Google login.', 'error')
        return redirect(url_for('auth.login'))

@bp.route('/google/callback')
def google_callback():
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": current_app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": current_app.config['GOOGLE_CLIENT_SECRET'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [current_app.config['GOOGLE_REDIRECT_URI']]
                }
            },
            scopes=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
        )
        flow.redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
        
        authorization_response = request.url
        flow.fetch_token(authorization_response=authorization_response)
        
        credentials = flow.credentials
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            current_app.config['GOOGLE_CLIENT_ID']
        )
        
        email = id_info.get('email')
        if not email:
            flash('Could not get email from Google.', 'error')
            return redirect(url_for('auth.login'))

        # Check if email domain is blocked
        if is_email_domain_blocked(email):
            flash('Email domain not allowed for registration or login.', 'error')
            return redirect(url_for('auth.login'))
            
        # Check if user exists - TRY CACHE FIRST
        cached_user_data = user_cache.get_user_by_email(email)
        if cached_user_data:
            logger.debug(f"🎯 Google OAuth user cache hit for: {email}")
            user = User.query.get(cached_user_data['id'])
        else:
            user = User.query.filter_by(email=email).first()
            if user:
                user_cache.cache_user_complete(user.to_dict())
                logger.debug(f"💾 Cached Google user data for: {email}")
        
        if not user:
            # Create new user
            username = id_info.get('name', email.split('@')[0])
            # Ensure username is unique
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                email=email,
                username=username,
                password_hash=generate_password_hash('google-oauth-user'),
                is_google_user=True,
                created_at=datetime.utcnow()
            )
            
            try:
                db.session.add(user)
                db.session.commit()
                # Cache the new user
                user_cache.cache_user_complete(user.to_dict())
                logger.debug(f"💾 Cached new Google user: {email}")
            except Exception as e:
                current_app.logger.error(f"Database error: {str(e)}")
                db.session.rollback()
                flash('An error occurred during registration.', 'error')
                return redirect(url_for('auth.login'))
        
        # Login user
        login_user(user, remember=True)
        
        # Log the login activity
        log_user_activity(user.id, 'login')
        
        flash('Logged in successfully with Google.', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        flash('Failed to log in with Google.', 'error')
        return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.register'))

        # Check if email domain is blocked
        if is_email_domain_blocked(email):
            flash('Email domain not allowed for registration.', 'error')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.register'))

        # Check if email exists - try cache first
        cached_user = user_cache.get_user_by_email(email)
        if cached_user or User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email.', 'error')
            return redirect(url_for('auth.register'))

        # Check if username exists - try cache first  
        cached_user = user_cache.get_user_by_username(username)
        if cached_user or User.query.filter_by(username=username).first():
            flash('Username already taken. Please use a different username.', 'error')
            return redirect(url_for('auth.register'))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            created_at=datetime.utcnow()
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            # Cache the new user
            user_cache.cache_user_complete(new_user.to_dict())
            logger.debug(f"💾 Cached new registered user: {email}")
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('auth.register'))

    return render_template('auth/register.html', title='Register')

@bp.route('/logout')
@login_required
def logout():
    # Log the logout activity
    if current_user.is_authenticated:
        log_user_activity(current_user.id, 'logout')
        
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Here you would send the password reset email
            flash('Check your email for instructions to reset your password.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Email address not found.', 'error')
            
    return render_template('auth/reset_password_request.html', title='Reset Password')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    user = User.verify_reset_password_token(token)
    if not user:
        flash('Invalid or expired reset token.', 'error')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.reset_password', token=token))
            
        user.set_password(password)
        db.session.commit()
        flash('Your password has been reset.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/reset_password.html', title='Reset Password')