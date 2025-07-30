"""
Pytest configuration and shared fixtures for Kyuaar tests
"""

import pytest
import os
import tempfile
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Set test environment
os.environ['TESTING'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['FIREBASE_STORAGE_BUCKET'] = 'test-bucket'

# Mock Firebase before importing app
with patch('firebase_admin.initialize_app'), \
     patch('firebase_admin.firestore.client'), \
     patch('firebase_admin.storage.bucket'):
    from app import app as flask_app


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': False
    })
    
    # Create a temporary directory for test uploads
    with tempfile.TemporaryDirectory() as temp_dir:
        flask_app.config['UPLOAD_FOLDER'] = temp_dir
        yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask application."""
    return app.test_cli_runner()


@pytest.fixture
def mock_db():
    """Mock Firebase Firestore database."""
    with patch('app.db') as mock:
        # Mock collection
        mock_collection = Mock()
        mock.collection.return_value = mock_collection
        
        # Mock document
        mock_doc = Mock()
        mock_collection.document.return_value = mock_doc
        
        # Mock query methods
        mock_collection.where.return_value = mock_collection
        mock_collection.order_by.return_value = mock_collection
        mock_collection.limit.return_value = mock_collection
        
        yield mock


@pytest.fixture
def mock_storage():
    """Mock Firebase Storage bucket."""
    with patch('app.bucket') as mock:
        mock_blob = Mock()
        mock.blob.return_value = mock_blob
        mock_blob.upload_from_file.return_value = None
        mock_blob.make_public.return_value = None
        mock_blob.public_url = 'https://storage.googleapis.com/test-bucket/test-file.png'
        
        yield mock


@pytest.fixture
def auth_headers():
    """Generate JWT auth headers for testing."""
    import jwt
    
    payload = {
        'user_id': 'test-user-123',
        'email': 'test@kyuaar.com',
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, 'test-secret-key', algorithm='HS256')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def sample_packet():
    """Sample packet data for testing."""
    return {
        'id': 'PKT-12345',
        'base_url': 'https://kyuaar.com/packet/PKT-12345',
        'qr_count': 25,
        'state': 'setup_pending',
        'config_state': 'pending',
        'price': 10.00,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        'id': 'USR-12345',
        'email': 'admin@kyuaar.com',
        'username': 'admin',
        'role': 'admin',
        'created_at': datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_sale():
    """Sample sale data for testing."""
    return {
        'packet_id': 'PKT-12345',
        'buyer_name': 'John Doe',
        'buyer_email': 'john@example.com',
        'sale_price': 10.00,
        'sale_date': datetime.utcnow().isoformat(),
        'payment_method': 'offline'
    }


@pytest.fixture
def mock_qr_image():
    """Create a mock QR code image file."""
    import io
    from PIL import Image
    
    # Create a simple test image
    img = Image.new('RGB', (200, 200), color='white')
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return img_io


@pytest.fixture(autouse=True)
def reset_db_mocks():
    """Reset database mocks before each test."""
    yield
    # Cleanup after test