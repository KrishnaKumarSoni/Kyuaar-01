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
try:
    # Use service account from environment or file
    if os.environ.get('FIREBASE_CREDENTIALS'):
        import json
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
    else:
        # Use the specific Firebase credentials file
        cred_file = 'kyuaar-01-firebase-adminsdk-fbsvc-6ffa60ee84.json'
        if os.path.exists(cred_file):
            cred = credentials.Certificate(cred_file)
            logger.info(f"Using credentials from: {cred_file}")
        else:
            # Fallback to the original name
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

# Register blueprints with web UI routes
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(dashboard_bp, url_prefix='/')
app.register_blueprint(packets_bp, url_prefix='/packets')
app.register_blueprint(config_bp, url_prefix='/config')

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

# Customer-facing landing page
@app.route('/')
def landing():
    """Public landing page for potential customers"""
    return render_template('landing.html')

# Redirect authenticated users to dashboard
@app.route('/app')
def app_redirect():
    """Redirect authenticated users to dashboard or login"""
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    else:
        return redirect(url_for('auth.login'))

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