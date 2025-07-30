"""
User model for Kyuaar platform
Handles user authentication and management with Firebase Firestore
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from firebase_admin import firestore
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class User(UserMixin):
    """User model with Firebase Firestore backend"""
    
    def __init__(self, user_id, email, name, password_hash=None, role='admin', created_at=None):
        self.id = user_id
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.role = role
        self.created_at = created_at or datetime.now(timezone.utc)
        self.is_active_user = True
    
    def check_password(self, password):
        """Check if provided password matches stored hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Set password hash for user"""
        self.password_hash = generate_password_hash(password)
    
    @staticmethod
    def get_by_email(email):
        """Retrieve user by email from Firestore"""
        try:
            db = firestore.client()
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            docs = query.get()
            
            if not docs:
                return None
            
            doc = docs[0]
            data = doc.to_dict()
            
            return User(
                user_id=doc.id,
                email=data.get('email'),
                name=data.get('name'),
                password_hash=data.get('password_hash'),
                role=data.get('role', 'admin'),
                created_at=data.get('created_at')
            )
        except Exception as e:
            logger.error(f"Error retrieving user by email {email}: {e}")
            return None
    
    @staticmethod
    def get_by_id(user_id):
        """Retrieve user by ID from Firestore"""
        try:
            db = firestore.client()
            doc_ref = db.collection('users').document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            return User(
                user_id=user_id,
                email=data.get('email'),
                name=data.get('name'),
                password_hash=data.get('password_hash'),
                role=data.get('role', 'admin'),
                created_at=data.get('created_at')
            )
        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {e}")
            return None
    
    @staticmethod
    def create(email, password, name, role='admin'):
        """Create new user in Firestore"""
        try:
            db = firestore.client()
            users_ref = db.collection('users')
            
            # Check if user already exists
            existing = User.get_by_email(email)
            if existing:
                logger.warning(f"Attempted to create duplicate user: {email}")
                return None
            
            # Create user data
            user_data = {
                'email': email,
                'name': name,
                'password_hash': generate_password_hash(password),
                'role': role,
                'created_at': datetime.now(timezone.utc),
                'last_login': None
            }
            
            # Add to Firestore
            doc_ref = users_ref.add(user_data)
            user_id = doc_ref[1].id
            
            logger.info(f"Created new user: {email}")
            
            return User(
                user_id=user_id,
                email=email,
                name=name,
                password_hash=user_data['password_hash'],
                role=role,
                created_at=user_data['created_at']
            )
            
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            return None
    
    def update_last_login(self):
        """Update last login timestamp"""
        try:
            db = firestore.client()
            doc_ref = db.collection('users').document(self.id)
            doc_ref.update({
                'last_login': datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Error updating last login for user {self.id}: {e}")
    
    def to_dict(self):
        """Convert user to dictionary representation"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }