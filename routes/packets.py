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
    """Create a new packet with pricing and QR image upload"""
    if request.method == 'POST':
        try:
            qr_count = int(request.form.get('qr_count', 25))
            price_per_scan = float(request.form.get('price_per_scan', 50))
            redirect_url = request.form.get('redirect_url', '').strip()
            
            # Validate inputs
            if qr_count < 1 or qr_count > 100:
                flash('QR count must be between 1 and 100', 'error')
                return render_template('packets/create.html')
            
            if price_per_scan < 1 or price_per_scan > 1000:
                flash('Price per scan must be between ₹1 and ₹1000', 'error')
                return render_template('packets/create.html')
            
            if not redirect_url:
                flash('Redirect URL is required', 'error')
                return render_template('packets/create.html')
            
            # Check if QR image was uploaded
            if 'qr_image' not in request.files or request.files['qr_image'].filename == '':
                flash('QR code image is required', 'error')
                return render_template('packets/create.html')
            
            # Calculate total price based on QR count
            total_price = qr_count * price_per_scan
            
            # Create packet with pricing and default redirect
            packet = Packet.create(
                user_id=current_user.id,
                qr_count=qr_count,
                price=total_price
            )
            
            if packet:
                # Set the default redirect URL
                packet.redirect_url = redirect_url
                packet.save()
                
                # TODO: Handle QR image upload here
                # For now, mark setup as complete
                packet.transition_to('setup_done')
                packet.save()
                
                flash('Packet created successfully with pricing configuration!', 'success')
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