"""
Dashboard routes for displaying user overview and statistics
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models.packet import Packet, PacketStates
from models.activity import Activity
import logging

dashboard_bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard view"""
    try:
        # Get user packets
        packets = Packet.get_by_user(current_user.id)
        
        # Calculate statistics
        stats = {
            'total_packets': len(packets),
            'active_packets': len([p for p in packets if p.state == PacketStates.CONFIG_DONE]),
            'total_scans': sum(getattr(p, 'scan_count', 0) for p in packets),
            'monthly_scans': 0  # Will be calculated when scan analytics is implemented
        }
        
        # Get recent packets (last 5)
        recent_packets = packets[:5] if packets else []
        
        # Get recent activity (last 10)
        recent_activity = Activity.get_recent_by_user(current_user.id, limit=10)
        
        return render_template(
            'dashboard/index.html',
            stats=stats,
            recent_packets=recent_packets,
            recent_activity=recent_activity,
            packets=packets
        )
        
    except Exception as e:
        logger.error(f"Dashboard error for user {current_user.id}: {e}")
        # Return with empty data on error
        return render_template(
            'dashboard/index.html',
            stats={
                'total_packets': 0,
                'active_packets': 0,
                'total_scans': 0,
                'monthly_scans': 0
            },
            recent_packets=[],
            recent_activity=[],
            packets=[]
        )