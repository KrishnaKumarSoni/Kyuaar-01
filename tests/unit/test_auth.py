"""
Unit tests for authentication module
Tests Flask-Login authentication, registration, and user management
"""

import pytest
import json
import jwt
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from werkzeug.security import generate_password_hash
from flask_login import current_user
from flask import request

from models.user import User
from routes.auth import generate_token, verify_token, token_required


class TestJWTFunctions:
    """Test JWT token generation and validation functions"""
    
    def test_generate_token_valid(self, app):
        """Test JWT token generation with valid user ID"""
        with app.app_context():
            user_id = 'test-user-123'
            token = generate_token(user_id)
            
            assert token is not None
            assert isinstance(token, str)
            
            # Decode and verify payload
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            assert payload['user_id'] == user_id
            assert 'exp' in payload
            assert 'iat' in payload
    
    def test_verify_token_valid(self, app):
        """Test JWT token verification with valid token"""
        with app.app_context():
            user_id = 'test-user-123'
            token = generate_token(user_id)
            
            payload = verify_token(token)
            
            assert payload is not None
            assert payload['user_id'] == user_id
    
    def test_verify_token_expired(self, app):
        """Test JWT token verification with expired token"""
        with app.app_context():
            # Create expired token
            expired_payload = {
                'user_id': 'test-user-123',
                'exp': datetime.now(timezone.utc) - timedelta(hours=1),
                'iat': datetime.now(timezone.utc) - timedelta(hours=2)
            }
            expired_token = jwt.encode(expired_payload, app.config['SECRET_KEY'], algorithm='HS256')
            
            payload = verify_token(expired_token)
            
            assert payload is None
    
    def test_verify_token_invalid(self, app):
        """Test JWT token verification with invalid token"""
        with app.app_context():
            invalid_token = "invalid.token.here"
            
            payload = verify_token(invalid_token)
            
            assert payload is None
    
    def test_token_required_decorator_valid_token(self, app):
        """Test token_required decorator with valid token"""
        with app.app_context():
            token = generate_token('test-user-123')
            
            # Test the decorator directly
            @token_required
            def test_function():
                return json.dumps({'message': 'success', 'user_id': request.user_id})
            
            # Mock request with valid token
            with app.test_request_context(headers={'Authorization': f'Bearer {token}'}):
                result = test_function()
                data = json.loads(result)
                assert data['message'] == 'success'
                assert data['user_id'] == 'test-user-123'
    
    def test_token_required_decorator_no_token(self, app):
        """Test token_required decorator without token"""
        with app.app_context():
            @token_required
            def test_function():
                return json.dumps({'message': 'success'})
            
            # Mock request without token
            with app.test_request_context():
                result = test_function()
                # The decorator returns a Flask response tuple
                assert isinstance(result, tuple)
                response_data, status_code = result
                assert status_code == 401
                if hasattr(response_data, 'data'):
                    data = json.loads(response_data.data)
                else:
                    data = json.loads(response_data)
                assert 'Token missing' in data['error']


class TestAuthEndpoints:
    """Test authentication API endpoints"""
    
    @patch('firebase_admin.firestore.client')
    @patch('models.user.User.get_by_email')
    @patch('models.user.User.create')
    def test_register_success(self, mock_user_create, mock_get_by_email, mock_firestore, client, app):
        """Test successful user registration"""
        # Mock User.get_by_email to return None (user doesn't exist)
        mock_get_by_email.return_value = None
        
        # Mock user creation
        mock_user = Mock()
        mock_user.id = 'new-user-123'
        mock_user.to_dict.return_value = {
            'id': 'new-user-123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        mock_user_create.return_value = mock_user
        
        with app.app_context():
            response = client.post('/auth/api/register', 
                json={
                    'name': 'Test User',
                    'email': 'test@example.com',
                    'password': 'password123'
                })
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert 'token' in data
            assert data['user']['email'] == 'test@example.com'
            assert data['user']['name'] == 'Test User'
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post('/auth/api/register', 
            json={
                'name': 'testuser'
                # missing email and password
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'required' in data['error'].lower()
    
    def test_register_short_password(self, client):
        """Test registration with password too short"""
        response = client.post('/auth/api/register', 
            json={
                'name': 'testuser',
                'email': 'test@example.com',
                'password': '123'  # too short
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'at least 8 characters' in data['error']
    
    @patch('models.user.User.get_by_email')
    def test_register_user_exists(self, mock_get_by_email, client):
        """Test registration when user already exists"""
        # Mock user exists
        mock_existing_user = Mock()
        mock_get_by_email.return_value = mock_existing_user
        
        response = client.post('/auth/api/register', 
            json={
                'name': 'existing_user',
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'already exists' in data['error']
    
    @patch('models.user.User.get_by_email')
    def test_login_success(self, mock_get_by_email, client, app):
        """Test successful user login"""
        # Mock user found
        mock_user = Mock()
        mock_user.id = 'user-123'
        mock_user.check_password.return_value = True
        mock_user.update_last_login = Mock()
        mock_user.to_dict.return_value = {
            'id': 'user-123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        mock_get_by_email.return_value = mock_user
        
        with app.app_context():
            response = client.post('/auth/api/login', 
                json={
                    'email': 'test@example.com',
                    'password': 'password123'
                })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'token' in data
            assert data['user']['email'] == 'test@example.com'
            
            # Verify last_login was updated
            mock_user.update_last_login.assert_called_once()
    
    def test_login_missing_fields(self, client):
        """Test login with missing credentials"""
        response = client.post('/auth/api/login', json={'email': 'test@example.com'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'required' in data['error'].lower()
    
    @patch('models.user.User.get_by_email')
    def test_login_user_not_found(self, mock_get_by_email, client):
        """Test login with non-existent user"""
        # Mock user not found
        mock_get_by_email.return_value = None
        
        response = client.post('/auth/api/login', 
            json={
                'email': 'nonexistent@example.com',
                'password': 'password123'
            })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Invalid credentials' in data['error']
    
    @patch('models.user.User.get_by_email')
    def test_login_wrong_password(self, mock_get_by_email, client):
        """Test login with incorrect password"""
        # Mock user found but wrong password
        mock_user = Mock()
        mock_user.check_password.return_value = False
        mock_get_by_email.return_value = mock_user
        
        response = client.post('/auth/api/login', 
            json={
                'email': 'test@example.com',
                'password': 'wrong_password'
            })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Invalid credentials' in data['error']
    
    def test_logout_success(self, client, app):
        """Test successful logout"""
        with app.app_context():
            token = generate_token('test-user-123')
            
            response = client.post('/auth/api/logout', headers={
                'Authorization': f'Bearer {token}'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'successful' in data['message']
    
    def test_logout_no_token(self, client):
        """Test logout without token"""
        response = client.post('/auth/api/logout')
        
        assert response.status_code == 401
    
    @patch('models.user.User.get_by_id')
    def test_verify_success(self, mock_get_by_id, client, app):
        """Test successful token verification"""
        # Mock user
        mock_user = Mock()
        mock_user.to_dict.return_value = {
            'id': 'test-user-123',
            'email': 'test@example.com',
            'name': 'Test User'
        }
        mock_get_by_id.return_value = mock_user
        
        with app.app_context():
            token = generate_token('test-user-123')
            
            response = client.get('/auth/api/verify', headers={
                'Authorization': f'Bearer {token}'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['valid'] is True
            assert 'user' in data
    
    @patch('models.user.User.get_by_id')
    @patch('firebase_admin.firestore.client')
    def test_change_password_success(self, mock_firestore, mock_get_by_id, client, app):
        """Test successful password change"""
        # Mock user
        mock_user = Mock()
        mock_user.check_password.return_value = True
        mock_user.set_password = Mock()
        mock_user.password_hash = 'new_hash'
        mock_get_by_id.return_value = mock_user
        
        # Mock firestore update
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_user_ref = Mock()
        mock_db.collection.return_value.document.return_value = mock_user_ref
        
        with app.app_context():
            token = generate_token('test-user-123')
            
            response = client.post('/auth/api/change-password', 
                headers={'Authorization': f'Bearer {token}'},
                json={
                    'old_password': 'old_password',
                    'new_password': 'new_password123'
                })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'successful' in data['message']
            
            # Verify password was updated
            mock_user.set_password.assert_called_once_with('new_password123')
            mock_user_ref.update.assert_called_once()


class TestAuthSecurity:
    """Test security aspects of authentication"""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        password = "test_password_123"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        
        # Hashes should be different (salt)
        assert hash1 != hash2
        
        # But both should verify against original password
        from werkzeug.security import check_password_hash
        assert check_password_hash(hash1, password)
        assert check_password_hash(hash2, password)
    
    def test_jwt_token_expiration(self, app):
        """Test JWT token contains proper expiration"""
        with app.app_context():
            user_id = 'test-user-123'
            token = generate_token(user_id)
            
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Check expiration is set to 24 hours from now
            exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            now = datetime.now(timezone.utc)
            time_diff = exp_time - now
            
            # Should be approximately 24 hours (with some tolerance)
            assert timedelta(hours=23, minutes=50) <= time_diff <= timedelta(hours=24, minutes=10)
    
    def test_token_bearer_format(self, app):
        """Test that bearer token format is handled correctly"""
        with app.app_context():
            token = generate_token('test-user-123')
            
            @token_required
            def test_function():
                return json.dumps({'success': True, 'user_id': request.user_id})
            
            # Test with Bearer prefix
            with app.test_request_context(headers={'Authorization': f'Bearer {token}'}):
                result = test_function()
                data = json.loads(result)
                assert data['success'] is True
                assert data['user_id'] == 'test-user-123'
            
            # Test without Bearer prefix (should also work based on decorator logic)
            with app.test_request_context(headers={'Authorization': token}):
                result = test_function()
                data = json.loads(result)
                assert data['success'] is True
                assert data['user_id'] == 'test-user-123'