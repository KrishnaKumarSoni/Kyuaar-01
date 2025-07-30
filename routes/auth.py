"""
Authentication routes for user login, registration, and session management
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import User
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Please provide both email and password', 'error')
            return render_template('auth/login.html')
        
        try:
            # Find user by email
            user = User.get_by_email(email)
            
            if user and user.check_password(password):
                login_user(user, remember=bool(remember))
                logger.info(f"User {email} logged in successfully")
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('dashboard.index'))
            else:
                flash('Invalid email or password', 'error')
                logger.warning(f"Failed login attempt for {email}")
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('auth/login.html')

# Registration removed - admin only application

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    email = current_user.email
    logout_user()
    logger.info(f"User {email} logged out")
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/check', methods=['GET'])
def check_auth():
    """Check authentication status (API endpoint)"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'name': current_user.name,
                'role': current_user.role
            }
        })
    else:
        return jsonify({'authenticated': False}), 401