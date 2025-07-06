from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User
from app.utils.email_validator import is_email_domain_blocked

bp = Blueprint('user', __name__)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        try:
            # Update username
            if username and username != current_user.username:
                if User.query.filter_by(username=username).first():
                    flash('Username is already taken.', 'error')
                    return redirect(url_for('user.profile'))
                current_user.username = username

            # Update email
            if email and email != current_user.email:
                # Check if email domain is blocked
                if is_email_domain_blocked(email):
                    flash('Email domain not allowed.', 'error')
                    return redirect(url_for('user.profile'))
                    
                if User.query.filter_by(email=email).first():
                    flash('Email is already registered.', 'error')
                    return redirect(url_for('user.profile'))
                current_user.email = email

            # Update password
            if current_password and new_password:
                if not check_password_hash(current_user.password_hash, current_password):
                    flash('Current password is incorrect.', 'error')
                    return redirect(url_for('user.profile'))
                current_user.password_hash = generate_password_hash(new_password)

            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('user.profile'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile.', 'error')
            return redirect(url_for('user.profile'))

    return render_template('user/profile.html')

@bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    try:
        user = User.query.get(current_user.id)
        db.session.delete(user)
        db.session.commit()
        flash('Your account has been deleted.', 'success')
        return redirect(url_for('main.index'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting your account.', 'error')
        return redirect(url_for('user.profile'))