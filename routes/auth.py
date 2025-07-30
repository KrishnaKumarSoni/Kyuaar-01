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

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters long')
        
        if not email or '@' not in email:
            errors.append('Please provide a valid email address')
        
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters long')
        
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        try:
            # Check if user already exists
            if User.get_by_email(email):
                flash('An account with this email already exists', 'error')
                return render_template('auth/register.html')
            
            # Create new user
            user = User.create(
                email=email,
                password=password,
                name=name
            )
            
            if user:
                login_user(user)
                logger.info(f"New user registered: {email}")
                flash('Account created successfully!', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Failed to create account. Please try again.', 'error')
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('auth/register.html')

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