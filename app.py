"""
Kyuaar.com Flask Backend
Main application entry point with Firebase integration
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, redirect, url_for, request, render_template
from flask_cors import CORS
from flask_login import LoginManager
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
def initialize_firebase():
    """Initialize Firebase with proper error handling and logging"""
    try:
        # Use service account from environment or file
        if os.environ.get('FIREBASE_CREDENTIALS'):
            import json
            logger.info("Using Firebase credentials from environment variable")
            creds_json = os.environ.get('FIREBASE_CREDENTIALS')
            logger.info(f"Credentials length: {len(creds_json) if creds_json else 0}")
            cred_dict = json.loads(creds_json)
            logger.info(f"Parsed credentials for project: {cred_dict.get('project_id')}")
            cred = credentials.Certificate(cred_dict)
        else:
            # Use the specific Firebase credentials file
            cred_file = 'kyuaar-01-firebase-adminsdk-fbsvc-6ffa60ee84.json'
            if os.path.exists(cred_file):
                cred = credentials.Certificate(cred_file)
                logger.info(f"Using credentials from file: {cred_file}")
            else:
                # Fallback to the original name
                cred_file = 'firebase-credentials.json'
                if os.path.exists(cred_file):
                    cred = credentials.Certificate(cred_file)
                    logger.info(f"Using fallback credentials file: {cred_file}")
                else:
                    raise FileNotFoundError("No Firebase credentials file found")
        
        # Initialize Firebase app if not already initialized
        if not firebase_admin._apps:
            storage_bucket = os.environ.get('FIREBASE_STORAGE_BUCKET', 'kyuaar-packets.appspot.com')
            logger.info(f"Initializing Firebase with storage bucket: {storage_bucket}")
            
            firebase_admin.initialize_app(cred, {
                'storageBucket': storage_bucket
            })
            logger.info("Firebase app initialized successfully")
        else:
            logger.info("Firebase app already initialized")
        
        # Test Firebase connection
        db = firestore.client()
        bucket = storage.bucket()
        
        # Test basic connectivity
        db.collection('_test').limit(1).get()
        logger.info("Firebase Firestore connection verified")
        
        bucket.get_blob('_test')  # This will not fail even if blob doesn't exist
        logger.info("Firebase Storage connection verified")
        
        return db, bucket
        
    except Exception as e:
        logger.error(f"Critical error initializing Firebase: {e}")
        logger.error(f"Environment variables:")
        logger.error(f"  FIREBASE_CREDENTIALS present: {bool(os.environ.get('FIREBASE_CREDENTIALS'))}")
        logger.error(f"  FIREBASE_STORAGE_BUCKET: {os.environ.get('FIREBASE_STORAGE_BUCKET')}")
        
        # Re-raise the exception to prevent the app from starting with broken Firebase
        raise e

# Initialize Firebase
db, bucket = initialize_firebase()

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    try:
        from models.user import User
        return User.get_by_id(user_id)
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {e}")
        return None

# Import blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.packets import packets_bp
from routes.config import config_bp
from routes.api import api_bp
from routes.qr import qr_bp

# Register blueprints with web UI routes
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp, url_prefix='/app')
app.register_blueprint(packets_bp, url_prefix='/packets')
app.register_blueprint(config_bp, url_prefix='/config')
app.register_blueprint(qr_bp, url_prefix='/qr')

# Register API blueprint
app.register_blueprint(api_bp, url_prefix='/api')

# Customer-facing packet redirect handler
@app.route('/packet/<packet_id>')
def handle_packet_redirect(packet_id):
    """Handle QR code scans and redirect based on packet state"""
    try:
        from models.packet import Packet, PacketStates
        from flask import render_template, redirect as flask_redirect
        
        # Get packet
        db = firestore.client()
        packet_doc = db.collection('packets').document(packet_id).get()
        
        if not packet_doc.exists:
            return render_template('error.html', 
                                 error_message="Invalid QR code",
                                 error_details="This QR code is not recognized."), 404
        
        packet_data = packet_doc.to_dict()
        packet = Packet.from_dict(packet_data)
        
        # Log scan
        scan_log = {
            'packet_id': packet_id,
            'scanned_at': datetime.now(timezone.utc),
            'user_agent': request.headers.get('User-Agent'),
            'ip_address': request.remote_addr
        }
        db.collection('scan_logs').add(scan_log)
        
        # Handle based on state
        if packet.state == PacketStates.SETUP_PENDING:
            return render_template('error.html',
                                 error_message="Packet not ready",
                                 error_details="This QR packet is being prepared. Please try again later."), 503
        
        elif packet.state == PacketStates.SETUP_DONE:
            return render_template('error.html',
                                 error_message="Packet not activated",
                                 error_details="This QR packet has not been activated yet. Please contact the seller."), 403
        
        elif packet.state == PacketStates.CONFIG_PENDING:
            # Show configuration page
            return render_template('configure.html',
                                 packet_id=packet_id,
                                 packet_data=packet_data)
        
        elif packet.state == PacketStates.CONFIG_DONE:
            # Redirect to configured URL
            redirect_url = packet.redirect_url
            if not redirect_url:
                return render_template('error.html',
                                     error_message="Configuration error",
                                     error_details="No redirect URL configured."), 500
            
            # Check if user wants to reconfigure
            if request.args.get('configure') == 'true':
                return render_template('configure.html',
                                     packet_id=packet_id,
                                     packet_data=packet_data,
                                     current_redirect=redirect_url)
            
            return flask_redirect(redirect_url)
        
        else:
            return render_template('error.html',
                                 error_message="Invalid state",
                                 error_details="Packet is in an invalid state."), 500
        
    except Exception as e:
        logger.error(f"Error handling packet redirect for {packet_id}: {e}")
        return render_template('error.html',
                             error_message="System error",
                             error_details="An error occurred processing your request."), 500

# Customer-facing landing page and authenticated user redirect
@app.route('/')
def landing():
    """Public landing page for potential customers, redirect authenticated users to dashboard"""
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    else:
        return render_template('landing.html')

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