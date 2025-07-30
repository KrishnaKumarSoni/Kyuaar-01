"""
Admin dashboard routes for business operations
Provides overview statistics and management capabilities
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from firebase_admin import firestore
from routes.auth import token_required
from collections import defaultdict

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

@admin_bp.route('/dashboard/stats')
@token_required
def dashboard_stats():
    """Get dashboard statistics"""
    try:
        db = firestore.client()
        
        # Get packet counts by state
        packets_ref = db.collection('packets')
        all_packets = list(packets_ref.where('deleted', '!=', True).stream())
        
        state_counts = defaultdict(int)
        total_revenue = 0.0
        total_scans = 0
        
        for packet_doc in all_packets:
            packet_data = packet_doc.to_dict()
            state_counts[packet_data['state']] += 1
            
            # Calculate revenue from sold packets
            if packet_data['state'] in ['config_pending', 'config_done']:
                total_revenue += packet_data.get('sale_price', 0)
            
            total_scans += packet_data.get('scan_count', 0)
        
        # Get recent sales (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_sales = []
        
        for packet_doc in all_packets:
            packet_data = packet_doc.to_dict()
            if packet_data.get('sold_at') and packet_data['sold_at'] > week_ago:
                recent_sales.append({
                    'packet_id': packet_doc.id,
                    'buyer_name': packet_data.get('buyer_name'),
                    'buyer_email': packet_data.get('buyer_email'),
                    'price': packet_data.get('sale_price'),
                    'sold_at': packet_data['sold_at'].isoformat()
                })
        
        # Sort recent sales by date
        recent_sales.sort(key=lambda x: x['sold_at'], reverse=True)
        recent_sales = recent_sales[:10]  # Limit to 10 most recent
        
        # Get pending configurations (sold but not configured)
        pending_configs = []
        for packet_doc in all_packets:
            packet_data = packet_doc.to_dict()
            if packet_data['state'] == 'config_pending':
                days_pending = (datetime.now(timezone.utc) - packet_data['sold_at']).days
                if days_pending > 3:  # Alert if pending for more than 3 days
                    pending_configs.append({
                        'packet_id': packet_doc.id,
                        'buyer_email': packet_data.get('buyer_email'),
                        'days_pending': days_pending
                    })
        
        stats = {
            'total_packets': len(all_packets),
            'packets_by_state': dict(state_counts),
            'total_revenue': round(total_revenue, 2),
            'total_scans': total_scans,
            'recent_sales': recent_sales,
            'pending_configurations': pending_configs,
            'alerts': {
                'pending_configs': len(pending_configs),
                'low_inventory': state_counts.get('setup_done', 0) < 5
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({'error': 'Failed to get statistics'}), 500

@admin_bp.route('/revenue/monthly')
@token_required
def monthly_revenue():
    """Get monthly revenue data for charts"""
    try:
        db = firestore.client()
        
        # Get all transactions
        transactions_ref = db.collection('transactions')
        transactions = list(transactions_ref.where('type', '==', 'sale').stream())
        
        # Group by month
        monthly_data = defaultdict(lambda: {'revenue': 0, 'count': 0})
        
        for trans_doc in transactions:
            trans_data = trans_doc.to_dict()
            created_at = trans_data['created_at']
            month_key = created_at.strftime('%Y-%m')
            
            monthly_data[month_key]['revenue'] += trans_data['amount']
            monthly_data[month_key]['count'] += 1
        
        # Convert to list and sort
        result = []
        for month, data in monthly_data.items():
            result.append({
                'month': month,
                'revenue': round(data['revenue'], 2),
                'sales_count': data['count']
            })
        
        result.sort(key=lambda x: x['month'])
        
        # Limit to last 12 months
        result = result[-12:]
        
        return jsonify({'monthly_revenue': result})
        
    except Exception as e:
        logger.error(f"Error getting monthly revenue: {e}")
        return jsonify({'error': 'Failed to get revenue data'}), 500

@admin_bp.route('/settings', methods=['GET'])
@token_required
def get_settings():
    """Get admin settings"""
    try:
        db = firestore.client()
        settings_doc = db.collection('settings').document('global').get()
        
        if settings_doc.exists:
            settings = settings_doc.to_dict()
        else:
            # Default settings
            settings = {
                'default_price_per_packet': 10.0,
                'default_qr_count': 25,
                'allow_customer_updates': True,
                'alert_days_pending': 7,
                'theme': {
                    'primary_color': '#CC5500',
                    'dark_mode': True
                }
            }
        
        return jsonify({'settings': settings})
        
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        return jsonify({'error': 'Failed to get settings'}), 500

@admin_bp.route('/settings', methods=['POST'])
@token_required
def update_settings():
    """Update admin settings"""
    try:
        data = request.get_json()
        
        db = firestore.client()
        settings_ref = db.collection('settings').document('global')
        
        # Update settings
        settings_ref.set(data, merge=True)
        
        logger.info(f"Settings updated by user {request.user_id}")
        
        return jsonify({'message': 'Settings updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({'error': 'Failed to update settings'}), 500

@admin_bp.route('/packets/bulk-action', methods=['POST'])
@token_required
def bulk_packet_action():
    """Perform bulk actions on packets"""
    try:
        data = request.get_json()
        action = data.get('action')
        packet_ids = data.get('packet_ids', [])
        
        if not action or not packet_ids:
            return jsonify({'error': 'Action and packet IDs required'}), 400
        
        db = firestore.client()
        batch = db.batch()
        
        for packet_id in packet_ids:
            packet_ref = db.collection('packets').document(packet_id)
            
            if action == 'delete':
                batch.update(packet_ref, {
                    'deleted': True,
                    'deleted_at': datetime.now(timezone.utc),
                    'deleted_by': request.user_id
                })
            elif action == 'reset_config':
                batch.update(packet_ref, {
                    'state': 'config_pending',
                    'redirect_url': None,
                    'configured_at': None
                })
            else:
                return jsonify({'error': 'Invalid action'}), 400
        
        # Commit batch
        batch.commit()
        
        logger.info(f"Bulk action {action} performed on {len(packet_ids)} packets")
        
        return jsonify({
            'message': f'Action completed on {len(packet_ids)} packets',
            'affected_count': len(packet_ids)
        })
        
    except Exception as e:
        logger.error(f"Error performing bulk action: {e}")
        return jsonify({'error': 'Failed to perform bulk action'}), 500