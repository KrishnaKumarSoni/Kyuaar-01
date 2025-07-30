"""
Unit tests for authentication module
Tests Flask-Login authentication, registration, and user management
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from werkzeug.security import generate_password_hash
from flask_login import current_user

from models.user import User


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
    
    def test_token_required_decorator_valid_token(self, app, client):
        """Test token_required decorator with valid token"""
        with app.app_context():
            token = generate_token('test-user-123')
            
            # Mock a protected route
            @app.route('/test-protected')
            @token_required
            def test_route():
                return json.dumps({'message': 'success', 'user_id': request.user_id})
            
            response = client.get('/test-protected', headers={
                'Authorization': f'Bearer {token}'
            })
            
            assert response.status_code == 200
    
    def test_token_required_decorator_no_token(self, app, client):
        """Test token_required decorator without token"""
        with app.app_context():
            # Mock a protected route
            @app.route('/test-protected-no-token')
            @token_required
            def test_route():
                return json.dumps({'message': 'success'})
            
            response = client.get('/test-protected-no-token')
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'Token missing' in data['error']


class TestAuthEndpoints:
    """Test authentication API endpoints"""
    
    @patch('routes.auth.firestore.client')
    def test_register_success(self, mock_firestore, client, app):
        """Test successful user registration"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock user doesn't exist
        mock_collection.where.return_value.limit.return_value.get.return_value = []
        
        # Mock user creation
        mock_ref = Mock()
        mock_ref.id = 'new-user-123'
        mock_collection.add.return_value = (None, mock_ref)
        
        with app.app_context():
            response = client.post('/api/auth/register', 
                json={
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'password': 'password123'
                })
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert 'token' in data
            assert data['user']['username'] == 'testuser'
            assert data['user']['email'] == 'test@example.com'
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post('/api/auth/register', 
            json={
                'username': 'testuser'
                # missing email and password
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'required' in data['error'].lower()
    
    def test_register_short_password(self, client):
        """Test registration with password too short"""
        response = client.post('/api/auth/register', 
            json={
                'username': 'testuser',
                'email': 'test@example.com',
                'password': '123'  # too short
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'at least 8 characters' in data['error']
    
    @patch('routes.auth.firestore.client')
    def test_register_user_exists(self, mock_firestore, client):
        """Test registration when user already exists"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock user exists
        mock_user_doc = Mock()
        mock_collection.where.return_value.limit.return_value.get.return_value = [mock_user_doc]
        
        response = client.post('/api/auth/register', 
            json={
                'username': 'existing_user',
                'email': 'test@example.com',
                'password': 'password123'
            })
        
        assert response.status_code == 409
        data = json.loads(response.data)
        assert 'already exists' in data['error']
    
    @patch('routes.auth.firestore.client')
    def test_login_success(self, mock_firestore, client, app):
        """Test successful user login"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock user found
        mock_user_doc = Mock()
        mock_user_doc.id = 'user-123'
        mock_user_doc.to_dict.return_value = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': generate_password_hash('password123')
        }
        mock_user_doc.reference.update = Mock()
        
        mock_collection.where.return_value.limit.return_value.get.return_value = [mock_user_doc]
        
        with app.app_context():
            response = client.post('/api/auth/login', 
                json={
                    'username': 'testuser',
                    'password': 'password123'
                })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'token' in data
            assert data['user']['username'] == 'testuser'
            
            # Verify last_login was updated
            mock_user_doc.reference.update.assert_called_once()
    
    def test_login_missing_fields(self, client):
        """Test login with missing credentials"""
        response = client.post('/api/auth/login', json={'username': 'testuser'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'required' in data['error'].lower()
    
    @patch('routes.auth.firestore.client')
    def test_login_user_not_found(self, mock_firestore, client):
        """Test login with non-existent user"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock user not found
        mock_collection.where.return_value.limit.return_value.get.return_value = []
        
        response = client.post('/api/auth/login', 
            json={
                'username': 'nonexistent',
                'password': 'password123'
            })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Invalid credentials' in data['error']
    
    @patch('routes.auth.firestore.client')
    def test_login_wrong_password(self, mock_firestore, client):
        """Test login with incorrect password"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock user found
        mock_user_doc = Mock()
        mock_user_doc.to_dict.return_value = {
            'username': 'testuser',
            'password_hash': generate_password_hash('correct_password')
        }
        
        mock_collection.where.return_value.limit.return_value.get.return_value = [mock_user_doc]
        
        response = client.post('/api/auth/login', 
            json={
                'username': 'testuser',
                'password': 'wrong_password'
            })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'Invalid credentials' in data['error']
    
    def test_logout_success(self, client, app):
        """Test successful logout"""
        with app.app_context():
            token = generate_token('test-user-123')
            
            response = client.post('/api/auth/logout', headers={
                'Authorization': f'Bearer {token}'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'successful' in data['message']
    
    def test_logout_no_token(self, client):
        """Test logout without token"""
        response = client.post('/api/auth/logout')
        
        assert response.status_code == 401
    
    @patch('routes.auth.firestore.client')
    def test_verify_success(self, mock_firestore, client, app):
        """Test successful token verification"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            'username': 'testuser',
            'email': 'test@example.com'
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        with app.app_context():
            token = generate_token('test-user-123')
            
            response = client.get('/api/auth/verify', headers={
                'Authorization': f'Bearer {token}'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['valid'] is True
            assert 'user' in data
    
    @patch('routes.auth.firestore.client')
    def test_change_password_success(self, mock_firestore, client, app):
        """Test successful password change"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {
            'username': 'testuser',
            'password_hash': generate_password_hash('old_password')
        }
        mock_user_doc.reference.update = Mock()
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_user_doc
        
        with app.app_context():
            token = generate_token('test-user-123')
            
            response = client.post('/api/auth/change-password', 
                headers={'Authorization': f'Bearer {token}'},
                json={
                    'old_password': 'old_password',
                    'new_password': 'new_password123'
                })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'successful' in data['message']
            
            # Verify password was updated
            mock_user_doc.reference.update.assert_called_once()


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
    
    def test_token_bearer_format(self, client, app):
        """Test that bearer token format is handled correctly"""
        with app.app_context():
            token = generate_token('test-user-123')
            
            # Mock a protected route for testing
            @app.route('/test-bearer')
            @token_required
            def test_route():
                return json.dumps({'success': True})
            
            # Test with Bearer prefix
            response = client.get('/test-bearer', headers={
                'Authorization': f'Bearer {token}'
            })
            assert response.status_code == 200
            
            # Test without Bearer prefix (should also work)
            response = client.get('/test-bearer', headers={
                'Authorization': token
            })
            assert response.status_code == 200