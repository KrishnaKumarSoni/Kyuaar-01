"""
Packet management routes for CRUD operations
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.packet import Packet
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
    """Create a new packet"""
    if request.method == 'POST':
        try:
            qr_count = int(request.form.get('qr_count', 25))
            
            # Validate QR count
            if qr_count < 1 or qr_count > 100:
                flash('QR count must be between 1 and 100', 'error')
                return render_template('packets/create.html')
            
            packet = Packet.create(
                user_id=current_user.id,
                qr_count=qr_count
            )
            
            if packet:
                flash('Packet created successfully!', 'success')
                return redirect(url_for('packets.view', packet_id=packet.id))
            else:
                flash('Failed to create packet', 'error')
                
        except ValueError:
            flash('Invalid QR count', 'error')
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

@packets_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload and scan QR codes"""
    packet_id = request.args.get('packet_id')
    packet = None
    
    if packet_id:
        packet = Packet.get_by_id_and_user(packet_id, current_user.id)
        if not packet:
            flash('Packet not found', 'error')
            return redirect(url_for('packets.list'))
    
    return render_template('packets/upload.html', packet=packet)

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
        
        # TODO: Add actual delete functionality to packet model
        # For now just show a message
        flash('Delete functionality will be implemented soon', 'info')
        return redirect(url_for('packets.list'))
        
    except Exception as e:
        logger.error(f"Error deleting packet {packet_id}: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('packets.list'))