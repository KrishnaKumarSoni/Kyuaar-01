"""
Pytest configuration and shared fixtures for Kyuaar tests
"""

import pytest
import os
import sys
import tempfile
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Set test environment BEFORE any imports
os.environ['TESTING'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['FIREBASE_STORAGE_BUCKET'] = 'test-bucket'

# Add project root to Python path 
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Create comprehensive Firebase mocks that persist for the entire test session
class MockFirebaseDoc:
    def __init__(self, data=None, exists=True):
        self._data = data or {}
        self.exists = exists
    
    def to_dict(self):
        return self._data
    
    def get(self):
        return self
    
    def set(self, data):
        self._data = data
    
    def update(self, data):
        self._data.update(data)
    
    def delete(self):
        self._data = {}
        self.exists = False


class MockFirebaseCollection:
    def __init__(self):
        self._docs = {}
    
    def document(self, doc_id):
        if doc_id not in self._docs:
            self._docs[doc_id] = MockFirebaseDoc()
        return self._docs[doc_id]
    
    def add(self, data):
        doc_id = f"doc_{len(self._docs)}"
        self._docs[doc_id] = MockFirebaseDoc(data)
        return type('MockRef', (), {'id': doc_id})()
    
    def where(self, *args):
        return self
    
    def order_by(self, *args):
        return self
    
    def limit(self, *args):
        return self
    
    def stream(self):
        return [doc for doc in self._docs.values() if doc.exists]


class MockFirebaseClient:
    def __init__(self):
        self._collections = {}
    
    def collection(self, name):
        if name not in self._collections:
            self._collections[name] = MockFirebaseCollection()
        return self._collections[name]


class MockStorageBlob:
    def __init__(self, name):
        self.name = name
        self.public_url = f'https://storage.googleapis.com/test-bucket/{name}'
    
    def upload_from_file(self, file_obj, content_type=None):
        return None
    
    def upload_from_string(self, data, content_type=None):
        return None
    
    def make_public(self):
        return None
    
    def delete(self):
        return None


class MockStorageBucket:
    def blob(self, name):
        return MockStorageBlob(name)


# Global mock instances
mock_db = MockFirebaseClient()
mock_bucket = MockStorageBucket()

# Start patches that will persist
firebase_patches = []

def start_firebase_patches():
    """Start Firebase patches that persist across all tests"""
    global firebase_patches, mock_db, mock_bucket
    
    # Mock firebase_admin functions
    init_patch = patch('firebase_admin.initialize_app', return_value=None)
    firestore_patch = patch('firebase_admin.firestore.client', return_value=mock_db)
    storage_patch = patch('firebase_admin.storage.bucket', return_value=mock_bucket)
    
    # Mock the app-level database and bucket
    app_db_patch = patch('app.db', mock_db)
    app_bucket_patch = patch('app.bucket', mock_bucket)
    
    firebase_patches = [init_patch, firestore_patch, storage_patch, app_db_patch, app_bucket_patch]
    
    for p in firebase_patches:
        p.start()

def stop_firebase_patches():
    """Stop all Firebase patches"""
    global firebase_patches
    for p in firebase_patches:
        try:
            p.stop()
        except:
            pass

# Start the patches immediately
start_firebase_patches()

# Now we can safely import the Flask app
try:
    from app import app as flask_app
except Exception as e:
    print(f"Error importing Flask app: {e}")
    # Create a minimal Flask app as fallback
    from flask import Flask
    flask_app = Flask(__name__)
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'


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
    """Return the global mock database."""
    global mock_db
    # Reset the mock database state for each test
    mock_db._collections = {}
    return mock_db


@pytest.fixture
def mock_storage():
    """Return the global mock storage."""
    global mock_bucket
    return mock_bucket


@pytest.fixture
def auth_headers(app):
    """Generate JWT auth headers for testing."""
    with app.app_context():
        try:
            from routes.auth import generate_token
            token = generate_token('test-user-123')
            return {'Authorization': f'Bearer {token}'}
        except Exception as e:
            # Fallback for when auth routes aren't available
            import jwt
            payload = {'user_id': 'test-user-123'}
            token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
            return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def authenticated_user():
    """Create a mock authenticated user for Flask-Login testing."""
    class MockUser:
        def __init__(self):
            self.id = 'test-user-123'
            self.email = 'admin@kyuaar.com'
            self.name = 'Test Admin'
            self.password_hash = 'test-hash'
            self.role = 'admin'
            self.is_authenticated = True
            self.is_active = True
            self.is_anonymous = False
        
        def get_id(self):
            return self.id
        
        def check_password(self, password):
            return password == 'testpassword'
        
        def to_dict(self):
            return {
                'id': self.id,
                'email': self.email,
                'name': self.name,
                'role': self.role
            }
    
    return MockUser()


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
    try:
        from PIL import Image
        # Create a simple test image
        img = Image.new('RGB', (200, 200), color='white')
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io
    except ImportError:
        # Fallback if PIL is not available
        return io.BytesIO(b'fake image data')


@pytest.fixture
def login_user(client, authenticated_user):
    """Helper to login a user for Flask-Login testing."""
    def _login(user=None):
        test_user = user or authenticated_user
        with client.session_transaction() as sess:
            sess['_user_id'] = test_user.id
            sess['_fresh'] = True
        return test_user
    return _login


# Clean up function to be called at the end of the test session
def pytest_sessionfinish(session, exitstatus):
    """Clean up after all tests are done"""
    stop_firebase_patches()