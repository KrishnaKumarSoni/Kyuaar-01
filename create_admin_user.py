#!/usr/bin/env python3
"""
Create Admin User Script for Kyuaar Platform
Initializes Firebase and creates the default admin user account
"""

import os
import sys
import logging
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Add the current directory to Python path so we can import models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Use the specific Firebase credentials file directly
        cred_file = 'kyuaar-01-firebase-adminsdk-fbsvc-6ffa60ee84.json'
        if os.path.exists(cred_file):
            cred = credentials.Certificate(cred_file)
            logger.info(f"Using credentials from: {cred_file}")
        else:
            raise FileNotFoundError(f"Firebase credentials file not found: {cred_file}")
        
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'kyuaar-packets.appspot.com')
        })
        
        logger.info("Firebase initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False

def create_admin_user():
    """Create the default admin user"""
    try:
        from models.user import User
        
        # Admin user credentials
        email = "admin@kyuaar.com"
        password = "admin123"
        name = "Administrator"
        role = "admin"
        
        logger.info(f"Creating admin user: {email}")
        
        # Check if user already exists
        existing_user = User.get_by_email(email)
        if existing_user:
            logger.warning(f"Admin user already exists: {email}")
            return existing_user
        
        # Create the admin user
        admin_user = User.create(
            email=email,
            password=password,
            name=name,
            role=role
        )
        
        if admin_user:
            logger.info(f"Successfully created admin user: {email}")
            logger.info(f"User ID: {admin_user.id}")
            return admin_user
        else:
            logger.error("Failed to create admin user")
            return None
            
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        return None

def verify_user_login(email, password):
    """Verify that the created user can login"""
    try:
        from models.user import User
        
        logger.info(f"Verifying login for: {email}")
        
        # Get user by email
        user = User.get_by_email(email)
        if not user:
            logger.error("User not found during verification")
            return False
        
        # Check password
        if user.check_password(password):
            logger.info("Password verification successful")
            return True
        else:
            logger.error("Password verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying user login: {e}")
        return False

def main():
    """Main function to create admin user"""
    print("Kyuaar Platform - Admin User Creation Script")
    print("=" * 50)
    
    # Initialize Firebase
    if not initialize_firebase():
        print("Failed to initialize Firebase. Exiting.")
        sys.exit(1)
    
    # Create admin user
    admin_user = create_admin_user()
    if not admin_user:
        print("Failed to create admin user. Exiting.")
        sys.exit(1)
    
    # Verify login
    if verify_user_login("admin@kyuaar.com", "admin123"):
        print("\n✅ SUCCESS!")
        print("Admin user created and verified successfully.")
        print("Login credentials:")
        print("  Email: admin@kyuaar.com")
        print("  Password: admin123")
        print("\nYou can now log in to the application.")
    else:
        print("\n❌ ERROR!")
        print("Admin user was created but login verification failed.")
        print("Please check the logs for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()