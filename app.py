"""
Kyuaar.com Flask Backend
Main application entry point with Firebase integration
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager
from datetime import timedelta
import firebase_admin
from firebase_admin import credentials, firestore, storage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Enable CORS for frontend integration
CORS(app, supports_credentials=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    # Use service account from environment or file
    if os.environ.get('FIREBASE_CREDENTIALS'):
        import json
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate('firebase-credentials.json')
    
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'kyuaar-packets.appspot.com')
    })
    
    # Initialize Firestore client
    db = firestore.client()
    bucket = storage.bucket()
    logger.info("Firebase initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    db = None
    bucket = None

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import blueprints
from routes.auth import auth_bp
from routes.packets import packets_bp
from routes.admin import admin_bp
from routes.redirect import redirect_bp
from routes.analytics import analytics_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(packets_bp, url_prefix='/api/packets')
app.register_blueprint(admin_bp, url_prefix='/api/admin')
app.register_blueprint(redirect_bp, url_prefix='/packet')
app.register_blueprint(analytics_bp, url_prefix='/api/analytics')

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    firebase_status = "connected" if db else "disconnected"
    return jsonify({
        'status': 'healthy',
        'firebase': firebase_status,
        'version': '1.0.0'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)