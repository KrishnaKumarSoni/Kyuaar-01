"""
Analytics and reporting endpoints for business intelligence
Track scans, conversions, and business metrics
"""

import logging
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from firebase_admin import firestore
from routes.auth import token_required
from collections import defaultdict

analytics_bp = Blueprint('analytics', __name__)
logger = logging.getLogger(__name__)

@analytics_bp.route('/scan-history')
@token_required
def scan_history():
    """Get scan history with filtering options"""
    try:
        db = firestore.client()
        
        # Parse query parameters
        days = int(request.args.get('days', 30))
        packet_id = request.args.get('packet_id')
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Build query
        scan_logs_ref = db.collection('scan_logs')
        query = scan_logs_ref.where('scanned_at', '>=', start_date)
        
        if packet_id:
            query = query.where('packet_id', '==', packet_id)
        
        # Get scan logs
        scan_logs = []
        for doc in query.stream():
            log_data = doc.to_dict()
            log_data['id'] = doc.id
            scan_logs.append(log_data)
        
        # Sort by scan time
        scan_logs.sort(key=lambda x: x['scanned_at'], reverse=True)
        
        return jsonify({
            'scan_logs': scan_logs,
            'count': len(scan_logs),
            'period_days': days
        })
        
    except Exception as e:
        logger.error(f"Error getting scan history: {e}")
        return jsonify({'error': 'Failed to get scan history'}), 500

@analytics_bp.route('/conversion-funnel')
@token_required
def conversion_funnel():
    """Get conversion funnel data"""
    try:
        db = firestore.client()
        
        # Get all packets
        packets_ref = db.collection('packets')
        packets = list(packets_ref.where('deleted', '!=', True).stream())
        
        funnel_data = {
            'created': 0,
            'setup_complete': 0,
            'sold': 0,
            'configured': 0,
            'conversion_rates': {}
        }
        
        for packet_doc in packets:
            packet_data = packet_doc.to_dict()
            state = packet_data['state']
            
            funnel_data['created'] += 1
            
            if state in ['setup_done', 'config_pending', 'config_done']:
                funnel_data['setup_complete'] += 1
            
            if state in ['config_pending', 'config_done']:
                funnel_data['sold'] += 1
            
            if state == 'config_done':
                funnel_data['configured'] += 1
        
        # Calculate conversion rates
        if funnel_data['created'] > 0:
            funnel_data['conversion_rates']['setup_rate'] = round(
                (funnel_data['setup_complete'] / funnel_data['created']) * 100, 2
            )
        
        if funnel_data['setup_complete'] > 0:
            funnel_data['conversion_rates']['sale_rate'] = round(
                (funnel_data['sold'] / funnel_data['setup_complete']) * 100, 2
            )
        
        if funnel_data['sold'] > 0:
            funnel_data['conversion_rates']['config_rate'] = round(
                (funnel_data['configured'] / funnel_data['sold']) * 100, 2
            )
        
        return jsonify(funnel_data)
        
    except Exception as e:
        logger.error(f"Error getting conversion funnel: {e}")
        return jsonify({'error': 'Failed to get conversion data'}), 500

@analytics_bp.route('/daily-scans')
@token_required
def daily_scans():
    """Get daily scan counts for charts"""
    try:
        db = firestore.client()
        
        # Get scan data for last 30 days
        days = int(request.args.get('days', 30))
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        scan_logs_ref = db.collection('scan_logs')
        scan_logs = list(scan_logs_ref.where('scanned_at', '>=', start_date).stream())
        
        # Group by date
        daily_counts = defaultdict(int)
        
        for log_doc in scan_logs:
            log_data = log_doc.to_dict()
            scan_date = log_data['scanned_at'].date()
            daily_counts[scan_date.isoformat()] += 1
        
        # Create complete date range with zeros for missing days
        result = []
        current_date = start_date.date()
        end_date = datetime.now(timezone.utc).date()
        
        while current_date <= end_date:
            date_str = current_date.isoformat()
            result.append({
                'date': date_str,
                'scans': daily_counts.get(date_str, 0)
            })
            current_date += timedelta(days=1)
        
        return jsonify({
            'daily_scans': result,
            'total_scans': sum(daily_counts.values()),
            'period_days': days
        })
        
    except Exception as e:
        logger.error(f"Error getting daily scans: {e}")
        return jsonify({'error': 'Failed to get scan data'}), 500

@analytics_bp.route('/popular-packets')
@token_required
def popular_packets():
    """Get most scanned packets"""
    try:
        db = firestore.client()
        
        # Get packets ordered by scan count
        packets_ref = db.collection('packets')
        packets = list(packets_ref.where('deleted', '!=', True).order_by('scan_count', direction='DESCENDING').limit(10).stream())
        
        popular_packets = []
        for packet_doc in packets:
            packet_data = packet_doc.to_dict()
            popular_packets.append({
                'packet_id': packet_doc.id,
                'scan_count': packet_data.get('scan_count', 0),
                'state': packet_data['state'],
                'buyer_name': packet_data.get('buyer_name'),
                'configured_at': packet_data.get('configured_at').isoformat() if packet_data.get('configured_at') else None
            })
        
        return jsonify({'popular_packets': popular_packets})
        
    except Exception as e:
        logger.error(f"Error getting popular packets: {e}")
        return jsonify({'error': 'Failed to get popular packets'}), 500

@analytics_bp.route('/sales-report')
@token_required
def sales_report():
    """Generate comprehensive sales report"""
    try:
        db = firestore.client()
        
        # Parse date range
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=timezone.utc)
            end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=timezone.utc)
        else:
            # Default to last 30 days
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
        
        # Get transactions in date range
        transactions_ref = db.collection('transactions')
        transactions = list(transactions_ref
                          .where('type', '==', 'sale')
                          .where('created_at', '>=', start_date)
                          .where('created_at', '<=', end_date)
                          .stream())
        
        # Calculate metrics
        total_sales = len(transactions)
        total_revenue = sum(trans.to_dict()['amount'] for trans in transactions)
        
        # Group by date for daily breakdown
        daily_sales = defaultdict(lambda: {'count': 0, 'revenue': 0})
        
        for trans_doc in transactions:
            trans_data = trans_doc.to_dict()
            date_key = trans_data['created_at'].date().isoformat()
            daily_sales[date_key]['count'] += 1
            daily_sales[date_key]['revenue'] += trans_data['amount']
        
        # Convert to list
        daily_breakdown = []
        for date, data in daily_sales.items():
            daily_breakdown.append({
                'date': date,
                'sales_count': data['count'],
                'revenue': round(data['revenue'], 2)
            })
        
        daily_breakdown.sort(key=lambda x: x['date'])
        
        # Get top buyers
        buyer_stats = defaultdict(lambda: {'count': 0, 'revenue': 0})
        
        for trans_doc in transactions:
            trans_data = trans_doc.to_dict()
            buyer_email = trans_data.get('buyer_email', 'Unknown')
            buyer_stats[buyer_email]['count'] += 1
            buyer_stats[buyer_email]['revenue'] += trans_data['amount']
        
        top_buyers = []
        for buyer, stats in buyer_stats.items():
            top_buyers.append({
                'buyer_email': buyer,
                'purchase_count': stats['count'],
                'total_spent': round(stats['revenue'], 2)
            })
        
        top_buyers.sort(key=lambda x: x['total_spent'], reverse=True)
        top_buyers = top_buyers[:10]  # Top 10 buyers
        
        report = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_sales': total_sales,
                'total_revenue': round(total_revenue, 2),
                'average_sale_value': round(total_revenue / total_sales, 2) if total_sales > 0 else 0
            },
            'daily_breakdown': daily_breakdown,
            'top_buyers': top_buyers
        }
        
        return jsonify(report)
        
    except Exception as e:
        logger.error(f"Error generating sales report: {e}")
        return jsonify({'error': 'Failed to generate sales report'}), 500

@analytics_bp.route('/performance-metrics')
@token_required
def performance_metrics():
    """Get key performance indicators"""
    try:
        db = firestore.client()
        
        # Get current period (last 30 days) and previous period for comparison
        current_end = datetime.now(timezone.utc)
        current_start = current_end - timedelta(days=30)
        previous_start = current_start - timedelta(days=30)
        
        def get_period_metrics(start_date, end_date):
            # Sales in period
            transactions = list(db.collection('transactions')
                              .where('type', '==', 'sale')
                              .where('created_at', '>=', start_date)
                              .where('created_at', '<', end_date)
                              .stream())
            
            sales_count = len(transactions)
            revenue = sum(trans.to_dict()['amount'] for trans in transactions)
            
            # Scans in period
            scans = list(db.collection('scan_logs')
                        .where('scanned_at', '>=', start_date)
                        .where('scanned_at', '<', end_date)
                        .stream())
            
            scan_count = len(scans)
            
            return {
                'sales': sales_count,
                'revenue': revenue,
                'scans': scan_count
            }
        
        current_metrics = get_period_metrics(current_start, current_end)
        previous_metrics = get_period_metrics(previous_start, current_start)
        
        # Calculate percentage changes
        def calc_change(current, previous):
            if previous == 0:
                return 0 if current == 0 else 100
            return round(((current - previous) / previous) * 100, 2)
        
        metrics = {
            'current_period': {
                'start_date': current_start.isoformat(),
                'end_date': current_end.isoformat(),
                'sales': current_metrics['sales'],
                'revenue': round(current_metrics['revenue'], 2),
                'scans': current_metrics['scans']
            },
            'changes': {
                'sales_change': calc_change(current_metrics['sales'], previous_metrics['sales']),
                'revenue_change': calc_change(current_metrics['revenue'], previous_metrics['revenue']),
                'scans_change': calc_change(current_metrics['scans'], previous_metrics['scans'])
            }
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': 'Failed to get performance metrics'}), 500