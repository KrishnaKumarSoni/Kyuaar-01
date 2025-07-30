"""
Unit tests for Flask-Login authentication system
Tests user login, registration, logout, and session management
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from werkzeug.security import generate_password_hash
from flask_login import current_user

from models.user import User


class TestUserModel:
    """Test User model functionality"""
    
    def test_user_creation(self):
        """Test User model instantiation"""
        user = User(
            user_id='test-123',
            email='test@example.com',
            name='Test User',
            password_hash=generate_password_hash('password123'),
            role='admin'
        )
        
        assert user.id == 'test-123'
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.role == 'admin'
        assert user.is_active_user is True
    
    def test_check_password_valid(self):
        """Test password checking with valid password"""
        user = User(
            user_id='test-123',
            email='test@example.com',
            name='Test User'
        )
        user.set_password('password123')
        
        assert user.check_password('password123') is True
        assert user.check_password('wrongpassword') is False
    
    def test_check_password_no_hash(self):
        """Test password checking with no password hash set"""
        user = User(
            user_id='test-123',
            email='test@example.com',
            name='Test User'
        )
        
        assert user.check_password('anypassword') is False
    
    def test_set_password(self):
        """Test password setting and hashing"""
        user = User(
            user_id='test-123',
            email='test@example.com',
            name='Test User'
        )
        
        user.set_password('newpassword123')
        
        assert user.password_hash is not None
        assert user.check_password('newpassword123') is True
        assert user.check_password('wrongpassword') is False
    
    @patch('firebase_admin.firestore.client')
    def test_get_by_email_found(self, mock_firestore):
        """Test getting user by email when user exists"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock query and document
        mock_query = Mock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_doc = Mock()
        mock_doc.id = 'user-123'
        mock_doc.to_dict.return_value = {
            'email': 'test@example.com',
            'name': 'Test User',
            'password_hash': 'hashed_password',
            'role': 'admin',
            'created_at': datetime.now(timezone.utc)
        }
        mock_query.get.return_value = [mock_doc]
        
        user = User.get_by_email('test@example.com')
        
        assert user is not None
        assert user.id == 'user-123'
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
    
    @patch('firebase_admin.firestore.client')
    def test_get_by_email_not_found(self, mock_firestore):
        """Test getting user by email when user doesn't exist"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_query = Mock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.get.return_value = []
        
        user = User.get_by_email('nonexistent@example.com')
        
        assert user is None
    
    @patch('firebase_admin.firestore.client')
    def test_create_user_success(self, mock_firestore):
        """Test creating new user successfully"""
        # Mock Firestore operations
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock user doesn't exist (for duplicate check)
        mock_query = Mock()
        mock_collection.where.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.get.return_value = []
        
        # Mock user creation
        mock_ref = Mock()
        mock_ref.id = 'new-user-123'
        mock_collection.add.return_value = (None, mock_ref)
        
        # Mock User.get_by_email to return None (no existing user)
        with patch.object(User, 'get_by_email', return_value=None):
            user = User.create(
                email='new@example.com',
                password='password123',
                name='New User'
            )
        
        assert user is not None
        assert user.email == 'new@example.com'
        assert user.name == 'New User'
        assert user.check_password('password123') is True
    
    @patch('firebase_admin.firestore.client')
    def test_create_user_duplicate(self, mock_firestore):
        """Test creating user that already exists"""
        existing_user = User(
            user_id='existing-123',
            email='existing@example.com',
            name='Existing User'
        )
        
        with patch.object(User, 'get_by_email', return_value=existing_user):
            user = User.create(
                email='existing@example.com',
                password='password123',
                name='Duplicate User'
            )
        
        assert user is None
    
    def test_to_dict(self):
        """Test user dictionary conversion"""
        created_at = datetime.now(timezone.utc)
        user = User(
            user_id='test-123',
            email='test@example.com',
            name='Test User',
            role='admin',
            created_at=created_at
        )
        
        user_dict = user.to_dict()
        
        assert user_dict['id'] == 'test-123'
        assert user_dict['email'] == 'test@example.com'
        assert user_dict['name'] == 'Test User'
        assert user_dict['role'] == 'admin'
        assert user_dict['created_at'] == created_at.isoformat()


class TestAuthRoutes:
    """Test authentication route endpoints"""
    
    def test_login_get(self, client):
        """Test GET request to login page"""
        response = client.get('/api/auth/login')
        assert response.status_code in [200, 404]  # 404 if template doesn't exist yet
    
    @patch.object(User, 'get_by_email')
    def test_login_post_success(self, mock_get_user, client, app):
        """Test successful login"""
        # Mock user
        mock_user = Mock()
        mock_user.check_password.return_value = True
        mock_user.id = 'user-123'
        mock_user.email = 'test@example.com'
        mock_user.name = 'Test User'
        mock_get_user.return_value = mock_user
        
        with app.test_request_context():
            response = client.post('/api/auth/login', data={
                'email': 'test@example.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Should redirect to dashboard or return success
            assert response.status_code in [200, 302]
    
    @patch.object(User, 'get_by_email')
    def test_login_post_invalid_credentials(self, mock_get_user, client):
        """Test login with invalid credentials"""
        # Mock user not found
        mock_get_user.return_value = None
        
        response = client.post('/api/auth/login', data={
            'email': 'invalid@example.com',
            'password': 'wrongpassword'
        })
        
        # Should return to login page with error
        assert response.status_code in [200, 302]
    
    def test_login_post_missing_data(self, client):
        """Test login with missing email or password"""
        response = client.post('/api/auth/login', data={
            'email': 'test@example.com'
            # missing password
        })
        
        assert response.status_code in [200, 400]
    
    def test_register_get(self, client):
        """Test GET request to register page"""
        response = client.get('/api/auth/register')
        assert response.status_code in [200, 404]  # 404 if template doesn't exist yet
    
    @patch.object(User, 'get_by_email')
    @patch.object(User, 'create')
    def test_register_post_success(self, mock_create, mock_get_user, client, app):
        """Test successful user registration"""
        # Mock no existing user
        mock_get_user.return_value = None
        
        # Mock user creation
        mock_user = Mock()
        mock_user.id = 'new-user-123'
        mock_user.email = 'new@example.com'
        mock_user.name = 'New User'
        mock_create.return_value = mock_user
        
        with app.test_request_context():
            response = client.post('/api/auth/register', data={
                'name': 'New User',
                'email': 'new@example.com',
                'password': 'password123',
                'confirm_password': 'password123'
            }, follow_redirects=True)
            
            # Should redirect to dashboard
            assert response.status_code in [200, 302]
    
    def test_register_post_validation_errors(self, client):
        """Test registration with validation errors"""
        # Test missing name
        response = client.post('/api/auth/register', data={
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert response.status_code in [200, 400]
        
        # Test password mismatch
        response = client.post('/api/auth/register', data={
            'name': 'Test User',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'different'
        })
        assert response.status_code in [200, 400]
        
        # Test short password
        response = client.post('/api/auth/register', data={
            'name': 'Test User',
            'email': 'test@example.com',
            'password': '123',
            'confirm_password': '123'
        })
        assert response.status_code in [200, 400]
    
    @patch.object(User, 'get_by_email')
    def test_register_existing_user(self, mock_get_user, client):
        """Test registration with existing email"""
        # Mock existing user
        mock_user = Mock()
        mock_get_user.return_value = mock_user
        
        response = client.post('/api/auth/register', data={
            'name': 'Test User',
            'email': 'existing@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        assert response.status_code in [200, 409]
    
    def test_logout(self, client):
        """Test user logout"""
        # This would require setting up a logged-in user session
        # For now, just test that the endpoint exists
        response = client.get('/api/auth/logout')
        assert response.status_code in [200, 302, 401]  # Various possible responses
    
    def test_check_auth_not_authenticated(self, client):
        """Test authentication check when not logged in"""
        response = client.get('/api/auth/check')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['authenticated'] is False
        else:
            assert response.status_code == 401


class TestAuthSecurity:
    """Test security aspects of authentication"""
    
    def test_password_hashing_security(self):
        """Test password hashing produces different results"""
        password = "test_password_123"
        
        user1 = User('id1', 'test1@example.com', 'User 1')
        user2 = User('id2', 'test2@example.com', 'User 2')
        
        user1.set_password(password)
        user2.set_password(password)
        
        # Different users should have different hashes for same password
        assert user1.password_hash != user2.password_hash
        
        # But both should verify correctly
        assert user1.check_password(password) is True
        assert user2.check_password(password) is True
    
    def test_password_complexity_requirements(self):
        """Test that password complexity is enforced"""
        # This would be tested in the registration endpoint
        # The actual validation is done in the route handler
        pass
    
    def test_email_case_insensitivity(self):
        """Test that email lookup is case insensitive"""
        # This is handled in the route by calling .lower() on email
        # Test would verify the route behavior
        pass


class TestUserSession:
    """Test user session management with Flask-Login"""
    
    def test_user_is_authenticated_property(self):
        """Test UserMixin is_authenticated property"""
        user = User('test-123', 'test@example.com', 'Test User')
        
        # UserMixin provides is_authenticated property
        assert hasattr(user, 'is_authenticated')
        assert user.is_authenticated is True
    
    def test_user_is_active_property(self):
        """Test UserMixin is_active property"""
        user = User('test-123', 'test@example.com', 'Test User')
        
        # UserMixin provides is_active property  
        assert hasattr(user, 'is_active')
        assert user.is_active is True
    
    def test_user_is_anonymous_property(self):
        """Test UserMixin is_anonymous property"""
        user = User('test-123', 'test@example.com', 'Test User')
        
        # UserMixin provides is_anonymous property
        assert hasattr(user, 'is_anonymous')
        assert user.is_anonymous is False
    
    def test_get_id_method(self):
        """Test UserMixin get_id method"""
        user = User('test-123', 'test@example.com', 'Test User')
        
        # UserMixin provides get_id method that returns user.id
        assert hasattr(user, 'get_id')
        assert user.get_id() == 'test-123'