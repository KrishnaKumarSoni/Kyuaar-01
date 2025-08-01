"""
API routes for JSON responses
Provides RESTful endpoints for frontend integration
"""

import logging
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from firebase_admin import firestore, storage
from models.packet import Packet, PacketStates
from models.activity import Activity, ActivityType
from models.user import User
from services.qr_generator import qr_generator

api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# ============= PACKET API ENDPOINTS =============

@api_bp.route('/packets', methods=['GET'])
@login_required
def get_packets():
    """Get all packets for current user"""
    try:
        packets = Packet.get_by_user(current_user.id)
        packets_data = [packet.to_dict() for packet in packets]
        
        return jsonify({
            'packets': packets_data,
            'count': len(packets_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting packets for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to retrieve packets'}), 500

@api_bp.route('/packets', methods=['POST'])
@login_required
def create_packet():
    """Create new packet"""
    try:
        data = request.get_json()
        
        qr_count = data.get('qr_count', 25)
        price = data.get('price')
        
        # Validate QR count
        if not isinstance(qr_count, int) or qr_count < 1 or qr_count > 100:
            return jsonify({'error': 'QR count must be between 1 and 100'}), 400
        
        # Create packet
        packet = Packet.create(
            user_id=current_user.id,
            qr_count=qr_count,
            price=price
        )
        
        if not packet:
            return jsonify({'error': 'Failed to create packet'}), 500
        
        # Get user's default QR settings
        user = User.get_by_id(current_user.id)
        default_settings = getattr(user, 'default_qr_settings', None) or {
            'module_drawer': 'square',
            'eye_drawer': 'square',
            'fill_color': '#000000',
            'back_color': '#FFFFFF',
            'box_size': 10,
            'border': 4
        }
        
        # Generate QR code with default style
        from services.qr_generator import qr_generator
        import base64
        
        # Create packet URL
        base_url = os.environ.get('BASE_URL', 'https://kyuaar.com')
        packet_url = f"{base_url}/packet/{packet.id}"
        
        # Generate QR
        qr_result = qr_generator.generate_qr_code(
            data=packet_url,
            packet_id=packet.id,
            settings=default_settings
        )
        
        if not qr_result['success']:
            logger.error(f"Failed to generate QR for packet {packet.id}: {qr_result.get('error')}")
            return jsonify({'error': 'Failed to generate QR code'}), 500
        
        # Save QR to Firebase
        image_data = base64.b64decode(qr_result['image_base64'])
        qr_url = qr_generator.save_to_firebase(
            image_data=image_data,
            filename="qr.png",
            packet_id=packet.id,
            settings=default_settings
        )
        
        if not qr_url:
            logger.error(f"Failed to save QR to Firebase for packet {packet.id}")
            return jsonify({'error': 'Failed to save QR code'}), 500
        
        # Update packet with QR URL and set to SETUP_DONE
        from models.packet import PacketStates
        packet.qr_image_url = qr_url
        packet.state = PacketStates.SETUP_DONE
        
        # Save updated packet
        db = firestore.client()
        packet_ref = db.collection('packets').document(packet.id)
        packet_ref.update({
            'qr_image_url': qr_url,
            'state': PacketStates.SETUP_DONE,
            'updated_at': datetime.now(timezone.utc)
        })
        
        # Log activity
        Activity.log(
            user_id=current_user.id,
            activity_type=ActivityType.PACKET_CREATED,
            title='Packet Created',
            description=f'Created packet {packet.id} with {qr_count} QR codes and auto-generated QR',
            metadata={'packet_id': packet.id, 'qr_count': qr_count, 'qr_url': qr_url}
        )
        
        return jsonify({
            'message': 'Packet created successfully with QR code',
            'packet': packet.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating packet: {e}")
        return jsonify({'error': 'Failed to create packet'}), 500

@api_bp.route('/packets/<packet_id>', methods=['GET'])
@login_required
def get_packet(packet_id):
    """Get specific packet"""
    try:
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            return jsonify({'error': 'Packet not found'}), 404
        
        return jsonify({'packet': packet.to_dict()})
        
    except Exception as e:
        logger.error(f"Error getting packet {packet_id}: {e}")
        return jsonify({'error': 'Failed to retrieve packet'}), 500

# QR upload endpoint removed - QR codes are now auto-generated during packet creation

@api_bp.route('/packets/<packet_id>/sell', methods=['POST'])
@login_required
def mark_packet_sold(packet_id):
    """Mark packet as sold"""
    try:
        data = request.get_json()
        
        buyer_name = data.get('buyer_name')
        buyer_email = data.get('buyer_email')
        sale_price = data.get('sale_price')
        
        if not buyer_name:
            return jsonify({'error': 'Buyer name is required'}), 400
        
        # Get packet
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            return jsonify({'error': 'Packet not found'}), 404
        
        # Mark as sold
        if packet.mark_sold(buyer_name, buyer_email, sale_price):
            packet.save()
            
            # Log activity
            Activity.log(
                user_id=current_user.id,
                activity_type=ActivityType.PACKET_SOLD,
                title='Packet Sold',
                description=f'Sold packet {packet_id} to {buyer_name}',
                metadata={
                    'packet_id': packet_id,
                    'buyer_name': buyer_name,
                    'buyer_email': buyer_email,
                    'sale_price': packet.sale_price
                }
            )
            
            return jsonify({
                'message': 'Packet marked as sold successfully',
                'packet': packet.to_dict()
            })
        else:
            return jsonify({'error': 'Cannot mark packet as sold in current state'}), 400
        
    except Exception as e:
        logger.error(f"Error marking packet {packet_id} as sold: {e}")
        return jsonify({'error': 'Failed to mark packet as sold'}), 500

@api_bp.route('/packets/<packet_id>', methods=['DELETE'])
@login_required
def delete_packet(packet_id):
    """Delete a packet via API"""
    try:
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            return jsonify({'error': 'Packet not found'}), 404
        
        # Delete the packet
        if packet.delete():
            # Log the deletion activity
            Activity.log(
                user_id=current_user.id,
                activity_type=ActivityType.PACKET_DELETED,
                title="Packet Deleted",
                description=f"Deleted packet with {packet.qr_count} QR codes",
                metadata={'packet_id': packet_id, 'qr_count': packet.qr_count}
            )
            
            return jsonify({'message': 'Packet deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete packet'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting packet {packet_id}: {e}")
        return jsonify({'error': 'Failed to delete packet'}), 500

# ============= USER STATISTICS API =============

@api_bp.route('/user/statistics', methods=['GET'])
@login_required
def get_user_statistics():
    """Get user statistics for dashboard"""
    try:
        # Get packet statistics
        packets = Packet.get_by_user(current_user.id)
        
        stats = {
            'total_packets': len(packets),
            'by_state': {
                'setup_pending': 0,
                'setup_done': 0,
                'config_pending': 0,
                'config_done': 0
            },
            'total_scans': 0,
            'total_revenue': 0.0
        }
        
        for packet in packets:
            stats['by_state'][packet.state] += 1
            # Note: scan count would need to be tracked separately in scan_logs
            if packet.is_sold():
                stats['total_revenue'] += packet.sale_price or 0
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting user statistics: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@api_bp.route('/user/activity', methods=['GET'])
@login_required
def get_user_activity():
    """Get recent user activity"""
    try:
        limit = int(request.args.get('limit', 10))
        activities = Activity.get_recent_by_user(current_user.id, limit)
        
        activities_data = []
        for activity in activities:
            activity_dict = activity.to_dict()
            # Format datetime for frontend
            if activity_dict['created_at']:
                activity_dict['created_at'] = activity.created_at.isoformat()
            activities_data.append(activity_dict)
        
        return jsonify({
            'activities': activities_data,
            'count': len(activities_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return jsonify({'error': 'Failed to get activity'}), 500

# ============= PACKET CONFIGURATION API (Customer-facing) =============

@api_bp.route('/packets/<packet_id>/configure', methods=['POST'])
def configure_packet_redirect(packet_id):
    """Configure packet redirect (customer-facing, no auth required)"""
    try:
        data = request.get_json()
        redirect_type = data.get('type', 'whatsapp')
        
        # Get packet (no user verification needed for customer configuration)
        db = firestore.client()
        packet_doc = db.collection('packets').document(packet_id).get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Invalid packet ID'}), 404
        
        packet_data = packet_doc.to_dict()
        packet = Packet.from_dict(packet_data)
        
        # Check if packet is in correct state for configuration
        if packet.state != PacketStates.CONFIG_PENDING:
            if packet.state == PacketStates.SETUP_PENDING:
                return jsonify({'error': 'Packet not ready for configuration'}), 400
            elif packet.state == PacketStates.SETUP_DONE:
                return jsonify({'error': 'Packet not yet sold'}), 400
            elif packet.state == PacketStates.CONFIG_DONE:
                # Allow reconfiguration if enabled
                pass
        
        # Build redirect URL based on type
        if redirect_type == 'whatsapp':
            phone = data.get('phone')
            if not phone:
                return jsonify({'error': 'Phone number required'}), 400
            
            # Clean phone number
            phone = ''.join(filter(str.isdigit, phone))
            if not phone.startswith('91'):  # Add India country code if missing
                phone = '91' + phone
            
            redirect_url = f'https://wa.me/{phone}'
            
        elif redirect_type == 'custom':
            redirect_url = data.get('url')
            if not redirect_url:
                return jsonify({'error': 'URL required'}), 400
            
            # Ensure URL has protocol
            if not redirect_url.startswith(('http://', 'https://')):
                redirect_url = 'https://' + redirect_url
        else:
            return jsonify({'error': 'Invalid redirect type'}), 400
        
        # Configure packet
        if packet.configure_redirect(redirect_url):
            packet.save()
            
            # Log activity for packet owner
            Activity.log(
                user_id=packet.user_id,
                activity_type=ActivityType.PACKET_CONFIGURED,
                title='Packet Configured',
                description=f'Customer configured packet {packet_id}',
                metadata={
                    'packet_id': packet_id,
                    'redirect_url': redirect_url,
                    'redirect_type': redirect_type
                }
            )
            
            return jsonify({
                'message': 'Packet configured successfully',
                'redirect_url': redirect_url
            })
        else:
            return jsonify({'error': 'Failed to configure packet'}), 500
        
    except Exception as e:
        logger.error(f"Error configuring packet {packet_id}: {e}")
        return jsonify({'error': 'Failed to configure packet'}), 500

@api_bp.route('/packets/<packet_id>/status', methods=['GET'])
def get_packet_status(packet_id):
    """Get packet status (customer-facing, no auth required)"""
    try:
        db = firestore.client()
        packet_doc = db.collection('packets').document(packet_id).get()
        
        if not packet_doc.exists:
            return jsonify({'error': 'Packet not found'}), 404
        
        packet_data = packet_doc.to_dict()
        
        return jsonify({
            'packet_id': packet_id,
            'state': packet_data['state'],
            'is_configured': packet_data['state'] == PacketStates.CONFIG_DONE,
            'redirect_url': packet_data.get('redirect_url'),
            'base_url': packet_data.get('base_url')
        })
        
    except Exception as e:
        logger.error(f"Error getting packet status: {e}")
        return jsonify({'error': 'Failed to get packet status'}), 500

# ============= SETTINGS API =============

@api_bp.route('/settings/qr-style', methods=['GET'])
@login_required
def get_qr_style_settings():
    """Get user's default QR style settings"""
    try:
        user = User.get_by_id(current_user.id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get default QR settings or return system defaults
        default_settings = getattr(user, 'default_qr_settings', None) or {
            'module_drawer': 'square',
            'eye_drawer': 'square',
            'fill_color': '#000000',
            'back_color': '#FFFFFF',
            'box_size': 10,
            'border': 4
        }
        
        return jsonify({
            'success': True,
            'settings': default_settings
        })
        
    except Exception as e:
        logger.error(f"Error getting QR style settings: {e}")
        return jsonify({'error': 'Failed to retrieve settings'}), 500

@api_bp.route('/settings/qr-style', methods=['POST'])
@login_required
def save_qr_style_settings():
    """Save user's default QR style settings"""
    try:
        data = request.get_json()
        settings = data.get('settings')
        
        if not settings:
            return jsonify({'error': 'No settings provided'}), 400
        
        # Validate settings
        required_fields = ['module_drawer', 'eye_drawer', 'fill_color', 'back_color', 'box_size', 'border']
        for field in required_fields:
            if field not in settings:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Update user document
        db = firestore.client()
        user_ref = db.collection('users').document(current_user.id)
        user_ref.update({
            'default_qr_settings': settings,
            'updated_at': datetime.now(timezone.utc)
        })
        
        # Log activity
        Activity.log(
            user_id=current_user.id,
            activity_type=ActivityType.SETTINGS_UPDATED,
            title='QR Style Updated',
            description='Updated default QR code style settings',
            metadata={'settings': settings}
        )
        
        return jsonify({
            'success': True,
            'message': 'QR style settings saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving QR style settings: {e}")
        return jsonify({'error': 'Failed to save settings'}), 500

# ============= QR CODE GENERATION API =============

@api_bp.route('/qr/generate', methods=['POST'])
@login_required
def generate_qr_code():
    """Generate QR code with custom styling"""
    try:
        data = request.get_json()
        
        # Validate required fields
        url = data.get('url')
        packet_id = data.get('packet_id')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Get settings
        settings = data.get('settings', {})
        
        # Generate QR code
        result = qr_generator.generate_qr_code(url, packet_id, settings)
        
        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Failed to generate QR code')}), 500
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return jsonify({'error': 'Failed to generate QR code'}), 500

@api_bp.route('/qr/save', methods=['POST'])
@login_required
def save_qr_code():
    """Save generated QR code to Firebase"""
    try:
        data = request.get_json()
        
        # Validate required fields
        image_base64 = data.get('image_base64')
        packet_id = data.get('packet_id')
        url = data.get('url')
        settings = data.get('settings', {})
        
        if not all([image_base64, url]):
            return jsonify({'error': 'Missing required fields: image_base64, url'}), 400
        
        # Verify packet ownership if packet_id is provided
        if packet_id:
            packet = Packet.get_by_id_and_user(packet_id, current_user.id)
            if not packet:
                return jsonify({'error': 'Packet not found'}), 404
        
        # Convert base64 to bytes
        import base64
        image_data = base64.b64decode(image_base64)
        
        # Generate filename
        packet_part = packet_id if packet_id else current_user.id
        filename = f"qr_code_{packet_part}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        # Save to Firebase Storage
        image_url = qr_generator.save_to_firebase(image_data, filename, packet_id, settings)
        
        if not image_url:
            return jsonify({'error': 'Failed to save image to Firebase'}), 500
        
        # Save record to Firestore (only if packet_id is provided)
        if packet_id:
            success = qr_generator.save_qr_record_to_firestore(packet_id, url, settings, image_url)
            if not success:
                return jsonify({'error': 'Failed to save QR code record'}), 500
        
        # Log activity
        Activity.log(
            user_id=current_user.id,
            activity_type=ActivityType.PACKET_UPLOADED,  # Reusing existing type
            title='QR Code Generated',
            description=f'Generated custom QR code for packet {packet_id}',
            metadata={
                'packet_id': packet_id,
                'url': url,
                'settings': settings,
                'image_url': image_url
            }
        )
        
        return jsonify({
            'message': 'QR code saved successfully',
            'image_url': image_url,
            'packet_id': packet_id
        })
        
    except Exception as e:
        logger.error(f"Error saving QR code: {e}")
        return jsonify({'error': 'Failed to save QR code'}), 500

@api_bp.route('/qr/presets', methods=['GET'])
@login_required
def get_qr_presets():
    """Get available QR code style presets"""
    try:
        presets = qr_generator.get_style_presets()
        return jsonify({'presets': presets})
        
    except Exception as e:
        logger.error(f"Error getting QR presets: {e}")
        return jsonify({'error': 'Failed to get QR presets'}), 500

@api_bp.route('/qr/packet/<packet_id>', methods=['GET'])
@login_required
def get_packet_qr_codes(packet_id):
    """Get all QR codes generated for a packet"""
    try:
        # Verify packet ownership
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            return jsonify({'error': 'Packet not found'}), 404
        
        # Get QR codes from Firestore
        db = firestore.client()
        qr_codes = []
        
        docs = db.collection('qr_codes').where('packet_id', '==', packet_id).get()
        
        for doc in docs:
            qr_data = doc.to_dict()
            qr_data['id'] = doc.id
            # Convert datetime to string for JSON serialization
            if 'created_at' in qr_data and qr_data['created_at']:
                qr_data['created_at'] = qr_data['created_at'].isoformat()
            if 'updated_at' in qr_data and qr_data['updated_at']:
                qr_data['updated_at'] = qr_data['updated_at'].isoformat()
            qr_codes.append(qr_data)
        
        return jsonify({
            'qr_codes': qr_codes,
            'count': len(qr_codes),
            'packet_id': packet_id
        })
        
    except Exception as e:
        logger.error(f"Error getting QR codes for packet {packet_id}: {e}")
        return jsonify({'error': 'Failed to get QR codes'}), 500