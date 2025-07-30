"""
Redirect handling for QR code scans
Customer-facing routes that don't require authentication
"""

import logging
from datetime import datetime, timezone
from flask import Blueprint, redirect, render_template, jsonify, request
from firebase_admin import firestore

redirect_bp = Blueprint('redirect', __name__)
logger = logging.getLogger(__name__)

@redirect_bp.route('/<packet_id>')
def handle_scan(packet_id):
    """Handle QR code scan and redirect based on packet state"""
    try:
        # Get packet
        db = firestore.client()
        packet_ref = db.collection('packets').document(packet_id)
        packet_doc = packet_ref.get()
        
        if not packet_doc.exists:
            return render_template('error.html', 
                                 error_message="Invalid QR code",
                                 error_details="This QR code is not recognized."), 404
        
        packet_data = packet_doc.to_dict()
        
        # Check if packet is deleted
        if packet_data.get('deleted', False):
            return render_template('error.html',
                                 error_message="QR code expired",
                                 error_details="This QR code is no longer active."), 410
        
        # Log scan
        scan_log = {
            'packet_id': packet_id,
            'scanned_at': datetime.now(timezone.utc),
            'user_agent': request.headers.get('User-Agent'),
            'ip_address': request.remote_addr
        }
        db.collection('scan_logs').add(scan_log)
        
        # Update scan count
        packet_ref.update({
            'scan_count': firestore.Increment(1),
            'last_scanned': datetime.now(timezone.utc)
        })
        
        # Handle based on state
        state = packet_data['state']
        
        if state == 'setup_pending':
            return render_template('error.html',
                                 error_message="Packet not ready",
                                 error_details="This QR packet is being prepared. Please try again later."), 503
        
        elif state == 'setup_done':
            return render_template('error.html',
                                 error_message="Packet not activated",
                                 error_details="This QR packet has not been activated yet. Please contact the seller."), 403
        
        elif state == 'config_pending':
            # Show configuration page
            return render_template('configure.html',
                                 packet_id=packet_id,
                                 packet_data=packet_data)
        
        elif state == 'config_done':
            # Redirect to configured URL
            redirect_url = packet_data.get('redirect_url')
            if not redirect_url:
                return render_template('error.html',
                                     error_message="Configuration error",
                                     error_details="No redirect URL configured."), 500
            
            # Check if updates are allowed
            if request.args.get('configure') == 'true' and packet_data.get('allow_updates', True):
                return render_template('configure.html',
                                     packet_id=packet_id,
                                     packet_data=packet_data,
                                     current_redirect=redirect_url)
            
            return redirect(redirect_url)
        
        else:
            return render_template('error.html',
                                 error_message="Invalid state",
                                 error_details="Packet is in an invalid state."), 500
        
    except Exception as e:
        logger.error(f"Error handling scan for packet {packet_id}: {e}")
        return render_template('error.html',
                             error_message="System error",
                             error_details="An error occurred processing your request."), 500

@redirect_bp.route('/<packet_id>/check')
def check_packet_state(packet_id):
    """API endpoint to check packet state (for AJAX calls)"""
    try:
        db = firestore.client()
        packet_doc = db.collection('packets').document(packet_id).get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Packet not found'}), 404
        
        packet_data = packet_doc.to_dict()
        
        return jsonify({
            'state': packet_data['state'],
            'configured': packet_data['state'] == 'config_done',
            'redirect_url': packet_data.get('redirect_url'),
            'allow_updates': packet_data.get('allow_updates', True)
        })
        
    except Exception as e:
        logger.error(f"Error checking packet state: {e}")
        return jsonify({'error': 'Failed to check packet state'}), 500