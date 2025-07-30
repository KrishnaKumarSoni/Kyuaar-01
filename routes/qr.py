"""
QR Code generation routes
Handles QR code creation interface and related functionality
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models.packet import Packet
import logging

qr_bp = Blueprint('qr', __name__)
logger = logging.getLogger(__name__)

@qr_bp.route('/generate')
@login_required
def generate():
    """QR code generation page"""
    try:
        # Get user packets for dropdown
        packets = Packet.get_by_user(current_user.id)
        
        return render_template(
            'qr/generate.html',
            packets=packets
        )
        
    except Exception as e:
        logger.error(f"Error loading QR generate page for user {current_user.id}: {e}")
        return render_template(
            'qr/generate.html',
            packets=[]
        )