"""
Packet management routes with state transition logic
Handles packet CRUD operations and lifecycle management
"""

import logging
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from firebase_admin import firestore, storage
from routes.auth import token_required
import os

packets_bp = Blueprint('packets', __name__)
logger = logging.getLogger(__name__)

# Packet states
PACKET_STATES = {
    'SETUP_PENDING': 'setup_pending',
    'SETUP_DONE': 'setup_done',
    'CONFIG_PENDING': 'config_pending',
    'CONFIG_DONE': 'config_done'
}

# Valid state transitions
VALID_TRANSITIONS = {
    'setup_pending': ['setup_done'],
    'setup_done': ['config_pending'],
    'config_pending': ['config_done'],
    'config_done': []  # Final state
}

def generate_packet_id():
    """Generate unique packet ID"""
    return str(uuid.uuid4())[:8]

def validate_state_transition(current_state, new_state):
    """Validate if state transition is allowed"""
    if new_state not in VALID_TRANSITIONS.get(current_state, []):
        return False
    return True

@packets_bp.route('/', methods=['GET'])
@token_required
def list_packets():
    """List all packets with filtering options"""
    try:
        db = firestore.client()
        packets_ref = db.collection('packets')
        
        # Apply filters
        state = request.args.get('state')
        buyer_email = request.args.get('buyer_email')
        
        query = packets_ref
        if state:
            query = query.where('state', '==', state)
        if buyer_email:
            query = query.where('buyer_email', '==', buyer_email)
        
        # Get packets
        packets = []
        for doc in query.stream():
            packet_data = doc.to_dict()
            packet_data['id'] = doc.id
            packets.append(packet_data)
        
        return jsonify({
            'packets': packets,
            'count': len(packets)
        })
        
    except Exception as e:
        logger.error(f"Error listing packets: {e}")
        return jsonify({'error': 'Failed to list packets'}), 500

@packets_bp.route('/', methods=['POST'])
@token_required
def create_packet():
    """Create new packet with unique ID and base URL"""
    try:
        data = request.get_json()
        
        # Validate input
        qr_count = data.get('qr_count', 25)
        if not isinstance(qr_count, int) or qr_count < 1 or qr_count > 100:
            return jsonify({'error': 'QR count must be between 1 and 100'}), 400
        
        # Generate unique packet ID
        packet_id = generate_packet_id()
        base_url = f"https://kyuaar.com/packet/{packet_id}"
        
        # Create packet document
        packet_data = {
            'packet_id': packet_id,
            'base_url': base_url,
            'qr_count': qr_count,
            'state': PACKET_STATES['SETUP_PENDING'],
            'created_at': datetime.now(timezone.utc),
            'created_by': request.user_id,
            'price': data.get('price', 10.0),  # Default $10
            'qr_image_url': None,
            'redirect_url': None,
            'buyer_name': None,
            'buyer_email': None,
            'sold_at': None,
            'configured_at': None,
            'scan_count': 0,
            'last_scanned': None
        }
        
        # Add to Firestore with packet_id as document ID
        db = firestore.client()
        db.collection('packets').document(packet_id).set(packet_data)
        
        # Log creation
        logger.info(f"Packet created: {packet_id} by user {request.user_id}")
        
        return jsonify({
            'message': 'Packet created successfully',
            'packet': packet_data
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating packet: {e}")
        return jsonify({'error': 'Failed to create packet'}), 500

@packets_bp.route('/<packet_id>', methods=['GET'])
@token_required
def get_packet(packet_id):
    """Get packet details by ID"""
    try:
        db = firestore.client()
        packet_doc = db.collection('packets').document(packet_id).get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Packet not found'}), 404
        
        packet_data = packet_doc.to_dict()
        packet_data['id'] = packet_doc.id
        
        return jsonify({'packet': packet_data})
        
    except Exception as e:
        logger.error(f"Error getting packet: {e}")
        return jsonify({'error': 'Failed to get packet'}), 500

@packets_bp.route('/<packet_id>/upload', methods=['POST'])
@token_required
def upload_qr_image(packet_id):
    """Upload QR image for packet and transition to SETUP_DONE"""
    try:
        # Check if file is in request
        if 'qr_image' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['qr_image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Invalid file type. Only PNG and JPG allowed'}), 400
        
        # Validate file size (5MB max)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 5 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum 5MB allowed'}), 400
        
        # Get packet
        db = firestore.client()
        packet_ref = db.collection('packets').document(packet_id)
        packet_doc = packet_ref.get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Packet not found'}), 404
        
        packet_data = packet_doc.to_dict()
        
        # Validate state transition
        if packet_data['state'] != PACKET_STATES['SETUP_PENDING']:
            return jsonify({'error': 'QR image already uploaded'}), 400
        
        # Upload to Firebase Storage
        bucket = storage.bucket()
        blob_name = f'qr_images/{packet_id}.{file_ext}'
        blob = bucket.blob(blob_name)
        
        # Upload file
        blob.upload_from_file(file, content_type=file.content_type)
        
        # Make blob publicly accessible
        blob.make_public()
        
        # Get public URL
        public_url = blob.public_url
        
        # Update packet with atomic transaction
        @firestore.transactional
        def update_packet(transaction):
            # Re-read packet in transaction
            packet_doc = transaction.get(packet_ref)
            if packet_doc.to_dict()['state'] != PACKET_STATES['SETUP_PENDING']:
                raise Exception('Invalid state for upload')
            
            transaction.update(packet_ref, {
                'qr_image_url': public_url,
                'state': PACKET_STATES['SETUP_DONE'],
                'uploaded_at': datetime.now(timezone.utc),
                'uploaded_by': request.user_id
            })
        
        # Execute transaction
        transaction = db.transaction()
        update_packet(transaction)
        
        logger.info(f"QR image uploaded for packet: {packet_id}")
        
        return jsonify({
            'message': 'QR image uploaded successfully',
            'image_url': public_url,
            'new_state': PACKET_STATES['SETUP_DONE']
        })
        
    except Exception as e:
        logger.error(f"Error uploading QR image: {e}")
        return jsonify({'error': 'Failed to upload QR image'}), 500

@packets_bp.route('/<packet_id>/sell', methods=['POST'])
@token_required
def mark_as_sold(packet_id):
    """Mark packet as sold (offline sale) and transition to CONFIG_PENDING"""
    try:
        data = request.get_json()
        
        # Validate input
        buyer_name = data.get('buyer_name')
        buyer_email = data.get('buyer_email')
        sale_price = data.get('price')
        
        if not buyer_name or not buyer_email:
            return jsonify({'error': 'Buyer name and email required'}), 400
        
        # Get packet
        db = firestore.client()
        packet_ref = db.collection('packets').document(packet_id)
        packet_doc = packet_ref.get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Packet not found'}), 404
        
        packet_data = packet_doc.to_dict()
        
        # Validate state
        if packet_data['state'] != PACKET_STATES['SETUP_DONE']:
            return jsonify({'error': 'Packet must be in SETUP_DONE state to sell'}), 400
        
        # Use provided price or default
        final_price = sale_price if sale_price is not None else packet_data['price']
        
        # Update packet with atomic transaction
        @firestore.transactional
        def update_packet(transaction):
            # Re-read packet in transaction
            packet_doc = transaction.get(packet_ref)
            if packet_doc.to_dict()['state'] != PACKET_STATES['SETUP_DONE']:
                raise Exception('Invalid state for sale')
            
            transaction.update(packet_ref, {
                'state': PACKET_STATES['CONFIG_PENDING'],
                'buyer_name': buyer_name,
                'buyer_email': buyer_email,
                'sale_price': final_price,
                'sold_at': datetime.now(timezone.utc),
                'sold_by': request.user_id
            })
            
            # Create sale transaction record
            transaction_data = {
                'packet_id': packet_id,
                'type': 'sale',
                'amount': final_price,
                'buyer_name': buyer_name,
                'buyer_email': buyer_email,
                'created_at': datetime.now(timezone.utc),
                'created_by': request.user_id
            }
            transaction.set(db.collection('transactions').document(), transaction_data)
        
        # Execute transaction
        transaction = db.transaction()
        update_packet(transaction)
        
        logger.info(f"Packet {packet_id} marked as sold to {buyer_email}")
        
        return jsonify({
            'message': 'Packet marked as sold successfully',
            'new_state': PACKET_STATES['CONFIG_PENDING'],
            'sale': {
                'buyer_name': buyer_name,
                'buyer_email': buyer_email,
                'price': final_price,
                'sold_at': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error marking packet as sold: {e}")
        return jsonify({'error': 'Failed to mark packet as sold'}), 500

@packets_bp.route('/<packet_id>/configure', methods=['POST'])
def configure_packet(packet_id):
    """Configure packet redirect (customer-facing, no auth required)"""
    try:
        data = request.get_json()
        redirect_type = data.get('type', 'whatsapp')
        
        # Get packet
        db = firestore.client()
        packet_ref = db.collection('packets').document(packet_id)
        packet_doc = packet_ref.get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Invalid QR code'}), 404
        
        packet_data = packet_doc.to_dict()
        
        # Check state
        if packet_data['state'] == PACKET_STATES['SETUP_PENDING']:
            return jsonify({'error': 'Packet not ready'}), 400
        elif packet_data['state'] == PACKET_STATES['SETUP_DONE']:
            return jsonify({'error': 'Packet not yet sold'}), 400
        elif packet_data['state'] == PACKET_STATES['CONFIG_DONE']:
            # Already configured, allow updates if enabled
            if not packet_data.get('allow_updates', True):
                return jsonify({'error': 'Configuration locked'}), 403
        
        # Build redirect URL based on type
        if redirect_type == 'whatsapp':
            phone = data.get('phone')
            if not phone:
                return jsonify({'error': 'Phone number required'}), 400
            
            # Clean phone number (remove spaces, dashes, etc.)
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('91'):  # Add country code if missing
                phone = '91' + phone
            
            redirect_url = f'https://wa.me/{phone}'
            
        elif redirect_type == 'custom':
            redirect_url = data.get('url')
            if not redirect_url:
                return jsonify({'error': 'URL required'}), 400
            
            # Validate URL
            if not redirect_url.startswith(('http://', 'https://')):
                redirect_url = 'https://' + redirect_url
        else:
            return jsonify({'error': 'Invalid redirect type'}), 400
        
        # Update packet with atomic transaction
        @firestore.transactional
        def update_packet(transaction):
            # Re-read packet in transaction
            packet_doc = transaction.get(packet_ref)
            current_state = packet_doc.to_dict()['state']
            
            if current_state not in [PACKET_STATES['CONFIG_PENDING'], PACKET_STATES['CONFIG_DONE']]:
                raise Exception('Invalid state for configuration')
            
            update_data = {
                'redirect_url': redirect_url,
                'redirect_type': redirect_type,
                'configured_at': datetime.now(timezone.utc)
            }
            
            # Update state if first configuration
            if current_state == PACKET_STATES['CONFIG_PENDING']:
                update_data['state'] = PACKET_STATES['CONFIG_DONE']
            
            transaction.update(packet_ref, update_data)
        
        # Execute transaction
        transaction = db.transaction()
        update_packet(transaction)
        
        logger.info(f"Packet {packet_id} configured with redirect to {redirect_url}")
        
        return jsonify({
            'message': 'Configuration saved successfully',
            'redirect_url': redirect_url
        })
        
    except Exception as e:
        logger.error(f"Error configuring packet: {e}")
        return jsonify({'error': 'Failed to configure packet'}), 500

@packets_bp.route('/<packet_id>', methods=['DELETE'])
@token_required
def delete_packet(packet_id):
    """Delete packet (soft delete by marking as deleted)"""
    try:
        db = firestore.client()
        packet_ref = db.collection('packets').document(packet_id)
        packet_doc = packet_ref.get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Packet not found'}), 404
        
        # Soft delete
        packet_ref.update({
            'deleted': True,
            'deleted_at': datetime.now(timezone.utc),
            'deleted_by': request.user_id
        })
        
        logger.info(f"Packet {packet_id} deleted by user {request.user_id}")
        
        return jsonify({'message': 'Packet deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting packet: {e}")
        return jsonify({'error': 'Failed to delete packet'}), 500