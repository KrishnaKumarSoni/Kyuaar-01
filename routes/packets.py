"""
Packet management routes for CRUD operations
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.packet import Packet, PacketStates
from models.user import User
from models.activity import Activity, ActivityType
from services.qr_generator import qr_generator
from firebase_admin import firestore
from datetime import datetime, timezone
import os
import base64
import logging

packets_bp = Blueprint('packets', __name__)
logger = logging.getLogger(__name__)

@packets_bp.route('/')
@packets_bp.route('/list')
@login_required
def list():
    """List all packets for the current user"""
    try:
        packets = Packet.get_by_user(current_user.id)
        return render_template('packets/list.html', packets=packets)
    except Exception as e:
        logger.error(f"Error listing packets for user {current_user.id}: {e}")
        flash('Error loading packets', 'error')
        return render_template('packets/list.html', packets=[])

@packets_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new packet with base URL generation"""
    if request.method == 'POST':
        try:
            qr_count = int(request.form.get('qr_count', 25))
            sale_price = float(request.form.get('sale_price', 500))
            
            # Validate inputs
            if qr_count < 1 or qr_count > 100:
                flash('QR count must be between 1 and 100', 'error')
                return render_template('packets/create.html')
            
            if sale_price < 0 or sale_price > 10000:
                flash('Sale price must be between ₹0 and ₹10,000', 'error')
                return render_template('packets/create.html')
            
            # Create packet with initial state: setup_pending
            packet = Packet.create(
                user_id=current_user.id,
                qr_count=qr_count,
                price=sale_price
            )
            
            if packet:
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
                
                # Generate both Main QR and Master QR with default style
                base_url = os.environ.get('BASE_URL', 'https://kyuaar.com')
                main_url = f"{base_url}/packet/{packet.id}"
                master_url = f"{base_url}/manage/{packet.master_id}"
                
                # Generate Main QR (customer-facing)
                main_qr_result = qr_generator.generate_qr_code(
                    data=main_url,
                    packet_id=packet.id,
                    settings=default_settings
                )
                
                # Generate Master QR (update/management)
                master_qr_result = qr_generator.generate_qr_code(
                    data=master_url,
                    packet_id=packet.master_id,
                    settings=default_settings
                )
                
                if main_qr_result and main_qr_result.get('success') and master_qr_result and master_qr_result.get('success'):
                    # Save both QRs to Firebase
                    try:
                        # Save Main QR
                        main_image_data = base64.b64decode(main_qr_result['image_base64'])
                        main_qr_url = qr_generator.save_to_firebase(
                            image_data=main_image_data,
                            filename="main_qr.png",
                            packet_id=packet.id,
                            settings=default_settings
                        )
                        
                        # Save Master QR
                        master_image_data = base64.b64decode(master_qr_result['image_base64'])
                        master_qr_url = qr_generator.save_to_firebase(
                            image_data=master_image_data,
                            filename="master_qr.png",
                            packet_id=packet.master_id,
                            settings=default_settings
                        )
                        
                        if main_qr_url and master_qr_url:
                            # Update packet with both QR URLs and set to SETUP_DONE
                            db = firestore.client()
                            packet_ref = db.collection('packets').document(packet.id)
                            packet_ref.update({
                                'qr_image_url': main_qr_url,
                                'master_qr_url': master_qr_url,
                                'state': PacketStates.SETUP_DONE,
                                'updated_at': datetime.now(timezone.utc)
                            })
                            
                            # Log activity
                            Activity.log(
                                user_id=current_user.id,
                                activity_type=ActivityType.PACKET_CREATED,
                                title='Packet Created',
                                description=f'Created packet {packet.id} with {qr_count} QR codes, Main QR and Master QR auto-generated',
                                metadata={'packet_id': packet.id, 'master_id': packet.master_id, 'qr_count': qr_count, 'main_qr_url': main_qr_url, 'master_qr_url': master_qr_url}
                            )
                            
                            flash('Packet created successfully with Main and Master QR codes!', 'success')
                        else:
                            logger.error(f"Failed to save QRs to Firebase for packet {packet.id}")
                            flash('Packet created but QR generation failed', 'warning')
                    except Exception as e:
                        logger.error(f"Error processing QRs for packet {packet.id}: {e}")
                        flash('Packet created but QR generation failed', 'warning')
                else:
                    logger.error(f"Failed to generate QRs for packet {packet.id}")
                    flash('Packet created but QR generation failed', 'warning')
                
                return redirect(url_for('packets.view', packet_id=packet.id))
            else:
                flash('Failed to create packet', 'error')
                
        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
        except Exception as e:
            logger.error(f"Error creating packet: {e}")
            flash('An error occurred while creating the packet', 'error')
    
    return render_template('packets/create.html')

@packets_bp.route('/<packet_id>')
@login_required
def view(packet_id):
    """View a specific packet"""
    try:
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            flash('Packet not found', 'error')
            return redirect(url_for('packets.list'))
        
        return render_template('packets/view.html', packet=packet)
    except Exception as e:
        logger.error(f"Error viewing packet {packet_id}: {e}")
        flash('Error loading packet', 'error')
        return redirect(url_for('packets.list'))

# Legacy route - redirect to create for unified workflow
@packets_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Legacy upload route - redirect to unified create workflow"""
    flash('QR upload is now part of the packet creation process', 'info')
    return redirect(url_for('packets.create'))

@packets_bp.route('/<packet_id>/sell', methods=['POST'])
@login_required
def mark_sold(packet_id):
    """Mark packet as sold"""
    try:
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            flash('Packet not found', 'error')
            return redirect(url_for('packets.list'))
        
        buyer_name = request.form.get('buyer_name', '').strip()
        buyer_email = request.form.get('buyer_email', '').strip()
        sale_price = request.form.get('sale_price')
        
        if not buyer_name:
            flash('Buyer name is required', 'error')
            return redirect(url_for('packets.view', packet_id=packet_id))
        
        try:
            sale_price = float(sale_price) if sale_price else None
        except ValueError:
            sale_price = None
        
        if packet.mark_sold(buyer_name, buyer_email, sale_price):
            packet.save()
            flash('Packet marked as sold successfully!', 'success')
        else:
            flash('Cannot mark packet as sold in current state', 'error')
        
        return redirect(url_for('packets.view', packet_id=packet_id))
        
    except Exception as e:
        logger.error(f"Error marking packet {packet_id} as sold: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('packets.list'))

@packets_bp.route('/<packet_id>/delete', methods=['POST'])
@login_required
def delete(packet_id):
    """Delete a packet"""
    try:
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            flash('Packet not found', 'error')
            return redirect(url_for('packets.list'))
        
        # Delete the packet
        if packet.delete():
            # Log the deletion activity
            from models.activity import Activity, ActivityType
            Activity.log(
                user_id=current_user.id,
                activity_type=ActivityType.PACKET_DELETED,
                title="Packet Deleted",
                description=f"Deleted packet with {packet.qr_count} QR codes",
                metadata={'packet_id': packet_id, 'qr_count': packet.qr_count}
            )
            
            flash('Packet deleted successfully', 'success')
        else:
            flash('Failed to delete packet', 'error')
        return redirect(url_for('packets.list'))
        
    except Exception as e:
        logger.error(f"Error deleting packet {packet_id}: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('packets.list'))