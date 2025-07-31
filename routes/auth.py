"""
Authentication routes for user login, registration, and session management
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import User
from functools import wraps
import jwt
import logging
from datetime import datetime, timedelta, timezone

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


# JWT Authentication Functions
def generate_token(user_id, expires_in_hours=24):
    """Generate JWT token for API authentication"""
    try:
        from flask import current_app
        payload = {
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
            'iat': datetime.now(timezone.utc)
        }
        token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        return token
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        return None


def verify_token(token):
    """Verify and decode JWT token"""
    try:
        from flask import current_app
        # Handle Bearer prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None


def token_required(f):
    """Decorator to require JWT token for API endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token missing'}), 401
        
        payload = verify_token(token)
        if payload is None:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user_id to request context for use in the decorated function
        request.user_id = payload['user_id']
        return f(*args, **kwargs)
    
    return decorated

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


# ============= JWT API ENDPOINTS =============

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API login endpoint that returns JWT token"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user by email
        user = User.get_by_email(email)
        
        if user and user.check_password(password):
            # Generate JWT token
            token = generate_token(user.id)
            
            if not token:
                return jsonify({'error': 'Failed to generate authentication token'}), 500
            
            # Update last login
            user.update_last_login()
            
            logger.info(f"API login successful for {email}")
            
            return jsonify({
                'message': 'Login successful',
                'token': token,
                'user': user.to_dict()
            })
        else:
            logger.warning(f"Failed API login attempt for {email}")
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        logger.error(f"API login error: {e}")
        return jsonify({'error': 'An error occurred during login'}), 500


@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API registration endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        email = data.get('email', '').lower().strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        if not all([email, password, name]):
            return jsonify({'error': 'Email, password, and name are required'}), 400
        
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Check if user already exists
        existing_user = User.get_by_email(email)
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Create new user
        user = User.create(email=email, password=password, name=name)
        
        if not user:
            return jsonify({'error': 'Failed to create user account'}), 500
        
        # Generate JWT token
        token = generate_token(user.id)
        
        if not token:
            return jsonify({'error': 'Account created but failed to generate token'}), 500
        
        logger.info(f"New user registered via API: {email}")
        
        return jsonify({
            'message': 'Registration successful',
            'token': token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"API registration error: {e}")
        return jsonify({'error': 'An error occurred during registration'}), 500


@auth_bp.route('/api/logout', methods=['POST'])
@token_required
def api_logout():
    """API logout endpoint"""
    try:
        # For JWT, logout is mainly client-side (delete token)
        # We could maintain a blacklist of tokens, but for simplicity, 
        # we'll just return success
        logger.info(f"API logout for user {request.user_id}")
        return jsonify({'message': 'Logout successful'})
        
    except Exception as e:
        logger.error(f"API logout error: {e}")
        return jsonify({'error': 'An error occurred during logout'}), 500


@auth_bp.route('/api/verify', methods=['GET'])
@token_required
def api_verify_token():
    """Verify JWT token and return user info"""
    try:
        # Get user by ID from token
        user = User.get_by_id(request.user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'valid': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"API token verification error: {e}")
        return jsonify({'error': 'Token verification failed'}), 500


@auth_bp.route('/api/change-password', methods=['POST'])
@token_required
def api_change_password():
    """Change user password via API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return jsonify({'error': 'Old password and new password are required'}), 400
        
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters long'}), 400
        
        # Get user
        user = User.get_by_id(request.user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify old password
        if not user.check_password(old_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Update password
        user.set_password(new_password)
        
        # Save to Firebase
        try:
            from firebase_admin import firestore
            db = firestore.client()
            user_ref = db.collection('users').document(user.id)
            user_ref.update({'password_hash': user.password_hash})
            
            logger.info(f"Password changed for user {user.id}")
            return jsonify({'message': 'Password changed successfully'})
            
        except Exception as e:
            logger.error(f"Error updating password in database: {e}")
            return jsonify({'error': 'Failed to update password'}), 500
        
    except Exception as e:
        logger.error(f"API change password error: {e}")
        return jsonify({'error': 'An error occurred while changing password'}), 500