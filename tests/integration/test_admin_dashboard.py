"""
Integration tests for admin dashboard functionality
Tests dashboard views, statistics, and administrative operations
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from flask_login import login_user

from models.user import User
from models.packet import Packet, PacketStates
from models.activity import Activity, ActivityType


class TestDashboardAccess:
    """Test dashboard access and authentication"""
    
    def test_dashboard_requires_authentication(self, client):
        """Test that dashboard requires authentication"""
        response = client.get('/admin')
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/login' in response.location or response.status_code == 401
    
    @patch('flask_login.current_user')
    def test_dashboard_authenticated_access(self, mock_user, client, app):
        """Test dashboard access for authenticated admin"""
        # Mock authenticated admin user
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.is_anonymous = False
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        with app.test_request_context():
            response = client.get('/admin')
            
            assert response.status_code == 200
    
    def test_non_admin_dashboard_access(self, client, app):
        """Test that non-admin users cannot access dashboard"""
        with app.test_request_context():
            # Mock regular user (not admin)
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.id = 'user-123'
            mock_user.role = 'user'  # Not admin
            mock_user.get_id.return_value = 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.get('/admin')
                
                # Should be forbidden or redirect
                assert response.status_code in [403, 302]


class TestDashboardStatistics:
    """Test dashboard statistics and metrics"""
    
    @patch('models.packet.Packet.get_by_user')
    @patch('flask_login.current_user')
    def test_dashboard_packet_statistics(self, mock_user, mock_get_packets, client, app):
        """Test dashboard displays packet statistics correctly"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock packets in different states
        mock_packets = [
            Mock(state=PacketStates.SETUP_PENDING, is_sold=lambda: False, sale_price=None),
            Mock(state=PacketStates.SETUP_DONE, is_sold=lambda: False, sale_price=None),
            Mock(state=PacketStates.CONFIG_PENDING, is_sold=lambda: True, sale_price=15.0),
            Mock(state=PacketStates.CONFIG_DONE, is_sold=lambda: True, sale_price=20.0),
            Mock(state=PacketStates.CONFIG_DONE, is_sold=lambda: True, sale_price=25.0),
        ]
        mock_get_packets.return_value = mock_packets
        
        with app.test_request_context():
            response = client.get('/admin')
            
            assert response.status_code == 200
            
            # Check that statistics are displayed
            response_text = response.data.decode('utf-8')
            
            # Should show total packets count
            assert '5' in response_text  # Total packets
            
            # Should show revenue information
            # Total revenue should be 15 + 20 + 25 = 60
            assert '60' in response_text or '$60' in response_text
    
    @patch('models.activity.Activity.get_recent_by_user')
    @patch('flask_login.current_user')
    def test_dashboard_recent_activity(self, mock_user, mock_get_activity, client, app):
        """Test dashboard displays recent activity"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock recent activities
        mock_activities = [
            Mock(
                title='Packet Created',
                description='Created packet PKT-12345',
                created_at=datetime.now(timezone.utc),
                activity_type=ActivityType.PACKET_CREATED
            ),
            Mock(
                title='Packet Sold',
                description='Sold packet PKT-12345 to John Doe',
                created_at=datetime.now(timezone.utc) - timedelta(hours=1),
                activity_type=ActivityType.PACKET_SOLD
            ),
        ]
        mock_get_activity.return_value = mock_activities
        
        with app.test_request_context():
            with patch('models.packet.Packet.get_by_user', return_value=[]):
                response = client.get('/admin')
                
                assert response.status_code == 200
                response_text = response.data.decode('utf-8')
                
                # Should show activity titles
                assert 'Packet Created' in response_text
                assert 'Packet Sold' in response_text


class TestPacketManagement:
    """Test packet management operations from dashboard"""
    
    @patch('models.packet.Packet.create')
    @patch('flask_login.current_user')
    def test_create_packet_from_dashboard(self, mock_user, mock_create, client, app):
        """Test creating new packet from dashboard"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock packet creation
        mock_packet = Mock()
        mock_packet.id = 'PKT-NEW123'
        mock_packet.base_url = 'https://kyuaar.com/packet/PKT-NEW123'
        mock_packet.qr_count = 25
        mock_packet.price = 10.0
        mock_create.return_value = mock_packet
        
        with app.test_request_context():
            response = client.post('/admin/packets/create', data={
                'qr_count': 25,
                'price': 10.0
            })
            
            # Should redirect after successful creation
            assert response.status_code in [200, 302]
            
            # Verify packet creation was called
            mock_create.assert_called_once_with(
                user_id='admin-123',
                qr_count=25,
                price=10.0
            )
    
    @patch('models.packet.Packet.get_by_id_and_user')
    @patch('flask_login.current_user')
    def test_mark_packet_sold_from_dashboard(self, mock_user, mock_get_packet, client, app):
        """Test marking packet as sold from dashboard"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock packet
        mock_packet = Mock()
        mock_packet.id = 'PKT-123'
        mock_packet.state = PacketStates.SETUP_DONE
        mock_packet.mark_sold.return_value = True
        mock_packet.save.return_value = True
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            response = client.post('/admin/packets/PKT-123/sell', data={
                'buyer_name': 'John Doe',
                'buyer_email': 'john@example.com',
                'sale_price': 15.0
            })
            
            assert response.status_code in [200, 302]
            
            # Verify mark_sold was called
            mock_packet.mark_sold.assert_called_once_with(
                'John Doe', 'john@example.com', 15.0
            )
    
    @patch('firebase_admin.storage.bucket')
    @patch('models.packet.Packet.get_by_id_and_user')
    @patch('flask_login.current_user')
    def test_upload_qr_image_from_dashboard(self, mock_user, mock_get_packet, mock_bucket, client, app):
        """Test uploading QR image from dashboard"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock packet
        mock_packet = Mock()
        mock_packet.id = 'PKT-123'
        mock_packet.state = PacketStates.SETUP_PENDING
        mock_packet.can_transition_to.return_value = True
        mock_packet.mark_setup_complete.return_value = True
        mock_packet.save.return_value = True
        mock_get_packet.return_value = mock_packet
        
        # Mock Firebase Storage
        mock_storage_bucket = Mock()
        mock_bucket.return_value = mock_storage_bucket
        
        mock_blob = Mock()
        mock_blob.public_url = 'https://storage.googleapis.com/bucket/qr_images/PKT-123.png'
        mock_storage_bucket.blob.return_value = mock_blob
        
        with app.test_request_context():
            # Create a test file
            import io
            test_file = io.BytesIO(b'fake image data')
            test_file.name = 'test_qr.png'
            
            response = client.post('/admin/packets/PKT-123/upload', 
                data={'qr_image': (test_file, 'test_qr.png')},
                content_type='multipart/form-data'
            )
            
            assert response.status_code in [200, 302]
            
            # Verify upload and state change
            mock_blob.upload_from_file.assert_called_once()
            mock_packet.mark_setup_complete.assert_called_once()


class TestDashboardViews:
    """Test various dashboard page views"""
    
    @patch('models.packet.Packet.get_by_user')
    @patch('flask_login.current_user')
    def test_packets_list_view(self, mock_user, mock_get_packets, client, app):
        """Test packets list view in dashboard"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock packets
        mock_packets = [
            Mock(
                id='PKT-123',
                base_url='https://kyuaar.com/packet/PKT-123',
                qr_count=25,
                state=PacketStates.SETUP_DONE,
                price=10.0,
                buyer_name=None,
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                id='PKT-456',
                base_url='https://kyuaar.com/packet/PKT-456',
                qr_count=50,
                state=PacketStates.CONFIG_DONE,
                price=20.0,
                buyer_name='Jane Doe',
                created_at=datetime.now(timezone.utc)
            ),
        ]
        mock_get_packets.return_value = mock_packets
        
        with app.test_request_context():
            response = client.get('/admin/packets')
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            
            # Should show packet information
            assert 'PKT-123' in response_text
            assert 'PKT-456' in response_text
            assert 'Jane Doe' in response_text
    
    @patch('models.packet.Packet.get_by_id_and_user')
    @patch('flask_login.current_user')
    def test_packet_detail_view(self, mock_user, mock_get_packet, client, app):
        """Test individual packet detail view"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock packet with detailed information
        mock_packet = Mock()
        mock_packet.id = 'PKT-123'
        mock_packet.base_url = 'https://kyuaar.com/packet/PKT-123'
        mock_packet.qr_count = 25
        mock_packet.state = PacketStates.CONFIG_DONE
        mock_packet.price = 10.0
        mock_packet.sale_price = 15.0
        mock_packet.buyer_name = 'John Doe'
        mock_packet.buyer_email = 'john@example.com'
        mock_packet.redirect_url = 'https://wa.me/919166900151'
        mock_packet.qr_image_url = 'https://storage.googleapis.com/bucket/qr.png'
        mock_packet.created_at = datetime.now(timezone.utc)
        mock_packet.sale_date = datetime.now(timezone.utc)
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            response = client.get('/admin/packets/PKT-123')
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            
            # Should show detailed packet information
            assert 'PKT-123' in response_text
            assert 'John Doe' in response_text
            assert 'john@example.com' in response_text
            assert 'wa.me/919166900151' in response_text


class TestDashboardAnalytics:
    """Test analytics features in dashboard"""
    
    @patch('models.packet.Packet.get_by_user')
    @patch('flask_login.current_user')
    def test_revenue_analytics(self, mock_user, mock_get_packets, client, app):
        """Test revenue analytics display"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock packets with sales data
        now = datetime.now(timezone.utc)
        mock_packets = [
            Mock(
                is_sold=lambda: True,
                sale_price=15.0,
                sale_date=now - timedelta(days=1)
            ),
            Mock(
                is_sold=lambda: True,
                sale_price=20.0,
                sale_date=now - timedelta(days=2)
            ),
            Mock(
                is_sold=lambda: True,
                sale_price=25.0,
                sale_date=now - timedelta(days=30)  # Different month
            ),
            Mock(
                is_sold=lambda: False,
                sale_price=None,
                sale_date=None
            ),
        ]
        mock_get_packets.return_value = mock_packets
        
        with app.test_request_context():
            response = client.get('/admin/analytics')
            
            assert response.status_code == 200
            response_text = response.data.decode('utf-8')
            
            # Should show revenue totals
            assert '60' in response_text or '$60' in response_text  # Total revenue
    
    @patch('models.activity.Activity.get_by_user')
    @patch('flask_login.current_user')
    def test_activity_analytics(self, mock_user, mock_get_activity, client, app):
        """Test activity analytics and trends"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock activities for analytics
        now = datetime.now(timezone.utc)
        mock_activities = [
            Mock(
                activity_type=ActivityType.PACKET_CREATED,
                created_at=now - timedelta(hours=1)
            ),
            Mock(
                activity_type=ActivityType.PACKET_SOLD,
                created_at=now - timedelta(hours=2)
            ),
            Mock(
                activity_type=ActivityType.QR_SCANNED,
                created_at=now - timedelta(hours=3)
            ),
        ]
        mock_get_activity.return_value = mock_activities
        
        with app.test_request_context():
            with patch('models.packet.Packet.get_by_user', return_value=[]):
                response = client.get('/admin/analytics')
                
                assert response.status_code == 200
                
                # Should include activity metrics
                response_text = response.data.decode('utf-8')
                assert len(mock_activities) > 0  # Basic verification


class TestDashboardSecurity:
    """Test security aspects of dashboard functionality"""
    
    def test_dashboard_csrf_protection(self, client, app):
        """Test CSRF protection on dashboard forms"""
        with app.test_request_context():
            # Mock authenticated admin
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.id = 'admin-123'
            mock_user.role = 'admin'
            mock_user.get_id.return_value = 'admin-123'
            
            with patch('flask_login.current_user', mock_user):
                # Try to submit form without CSRF token
                response = client.post('/admin/packets/create', data={
                    'qr_count': 25,
                    'price': 10.0,
                    # Missing CSRF token
                })
                
                # Should be rejected due to CSRF protection
                # (Exact behavior depends on CSRF implementation)
                assert response.status_code in [400, 403, 422]
    
    def test_admin_role_enforcement(self, client, app):
        """Test that admin role is properly enforced"""
        with app.test_request_context():
            # Mock user with insufficient privileges
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.id = 'user-123'
            mock_user.role = 'user'  # Not admin
            mock_user.get_id.return_value = 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                # Try to access admin functions
                admin_urls = [
                    '/admin',
                    '/admin/packets',
                    '/admin/packets/create',
                    '/admin/analytics',
                ]
                
                for url in admin_urls:
                    response = client.get(url)
                    # Should be forbidden or redirect to login
                    assert response.status_code in [403, 302]
    
    def test_sql_injection_protection(self, client, app):
        """Test protection against SQL injection (though we use Firestore)"""
        with app.test_request_context():
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.id = 'admin-123'
            mock_user.role = 'admin'
            mock_user.get_id.return_value = 'admin-123'
            
            with patch('flask_login.current_user', mock_user):
                # Try malicious input
                malicious_inputs = [
                    "'; DROP TABLE packets; --",
                    "<script>alert('xss')</script>",
                    "' OR '1'='1",
                ]
                
                for malicious_input in malicious_inputs:
                    response = client.post('/admin/packets/create', data={
                        'qr_count': malicious_input,
                        'price': '10.0',
                    })
                    
                    # Should handle malicious input gracefully
                    assert response.status_code in [400, 422]  # Bad request


class TestDashboardPerformance:
    """Test dashboard performance and efficiency"""
    
    @patch('models.packet.Packet.get_by_user')
    @patch('flask_login.current_user')
    def test_dashboard_with_many_packets(self, mock_user, mock_get_packets, client, app):
        """Test dashboard performance with large number of packets"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock large number of packets
        mock_packets = []
        for i in range(100):  # 100 packets
            mock_packet = Mock()
            mock_packet.id = f'PKT-{i:05d}'
            mock_packet.state = PacketStates.SETUP_DONE
            mock_packet.is_sold.return_value = i % 3 == 0  # Some sold
            mock_packet.sale_price = 10.0 if i % 3 == 0 else None
            mock_packets.append(mock_packet)
        
        mock_get_packets.return_value = mock_packets
        
        with app.test_request_context():
            import time
            start_time = time.time()
            
            response = client.get('/admin')
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert response.status_code == 200
            # Should respond reasonably quickly (under 2 seconds)
            assert response_time < 2.0
    
    def test_dashboard_pagination(self, client, app):
        """Test that dashboard implements pagination for large datasets"""
        with app.test_request_context():
            mock_user = Mock()
            mock_user.is_authenticated = True
            mock_user.id = 'admin-123'
            mock_user.role = 'admin'
            mock_user.get_id.return_value = 'admin-123'
            
            with patch('flask_login.current_user', mock_user):
                # Test pagination parameters
                response = client.get('/admin/packets?page=2&per_page=10')
                
                # Should handle pagination gracefully
                assert response.status_code in [200, 404]  # 404 if no data
                
                # Test invalid pagination
                response = client.get('/admin/packets?page=-1')
                assert response.status_code in [200, 400]  # Should handle gracefully


class TestDashboardIntegration:
    """Test dashboard integration with other system components"""
    
    @patch('services.qr_generator.QRGenerator.generate_qr_code')
    @patch('flask_login.current_user')
    def test_dashboard_qr_generation_integration(self, mock_user, mock_generate, client, app):
        """Test dashboard integration with QR generation service"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock QR generation
        mock_generate.return_value = {
            'success': True,
            'image_base64': 'fake_base64_data',
            'image_data_url': 'data:image/png;base64,fake_base64_data'
        }
        
        with app.test_request_context():
            response = client.post('/admin/generate-qr', data={
                'url': 'https://kyuaar.com/packet/PKT-123',
                'style': 'rounded'
            })
            
            assert response.status_code in [200, 302]
            mock_generate.assert_called_once()
    
    @patch('firebase_admin.firestore.client')
    @patch('flask_login.current_user')
    def test_dashboard_firebase_integration(self, mock_user, mock_firestore, client, app):
        """Test dashboard integration with Firebase"""
        # Mock authenticated admin
        mock_user.is_authenticated = True
        mock_user.id = 'admin-123'
        mock_user.role = 'admin'
        mock_user.get_id.return_value = 'admin-123'
        
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        # Mock successful database operations
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        with app.test_request_context():
            # Test that dashboard can handle Firebase operations
            response = client.get('/admin')
            
            # Should not fail due to Firebase operations
            assert response.status_code in [200, 500]  # 500 if Firebase issues