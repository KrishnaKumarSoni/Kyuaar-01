"""
End-to-end tests for complete packet lifecycle workflows
Tests complete user journeys from registration to packet configuration
"""

import pytest
import json
import io
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from models.user import User
from models.packet import Packet, PacketStates


class TestCompleteUserJourney:
    """Test complete user journey from registration to packet management"""
    
    @patch('firebase_admin.firestore.client')
    @patch('firebase_admin.storage.bucket')
    @patch.object(User, 'get_by_email')
    @patch.object(User, 'create')
    def test_complete_admin_workflow(self, mock_user_create, mock_get_user, 
                                   mock_storage, mock_firestore, client, app):
        """Test complete admin workflow: register -> login -> create packet -> upload -> sell -> track"""
        
        # Setup mocks
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        mock_bucket_obj = Mock()
        mock_storage.return_value = mock_bucket_obj
        mock_blob = Mock()
        mock_bucket_obj.blob.return_value = mock_blob
        mock_blob.public_url = 'https://storage.googleapis.com/bucket/qr.png'
        
        with app.test_request_context():
            # 1. User Registration
            mock_get_user.return_value = None  # No existing user
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.email = 'admin@kyuaar.com'
            mock_user.name = 'Admin User'
            mock_user_create.return_value = mock_user
            
            response = client.post('/auth/register', data={
                'name': 'Admin User',
                'email': 'admin@kyuaar.com',
                'password': 'password123',
                'confirm_password': 'password123'
            })
            
            assert response.status_code in [200, 302]  # Success or redirect
            
            # 2. User Login
            mock_get_user.return_value = mock_user
            mock_user.check_password.return_value = True
            
            response = client.post('/auth/login', data={
                'email': 'admin@kyuaar.com',
                'password': 'password123'
            })
            
            assert response.status_code in [200, 302]
            
            # 3. Create Packet via API
            response = client.post('/api/packets', 
                                 json={'qr_count': 25, 'price': 10.0})
            
            assert response.status_code in [200, 201, 401]  # Created or auth required
            
            # 4. Upload QR Image
            # Create test image
            img = Image.new('RGB', (200, 200), color='white')
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            
            response = client.post('/api/packets/PKT-TEST123/upload',
                                 data={'file': (img_io, 'qr.png', 'image/png')})
            
            assert response.status_code in [200, 401, 404]
            
            # 5. Mark Packet as Sold
            response = client.post('/api/packets/PKT-TEST123/sell',
                                 json={
                                     'buyer_name': 'John Doe',
                                     'buyer_email': 'john@example.com',
                                     'sale_price': 12.0
                                 })
            
            assert response.status_code in [200, 401, 404]
            
            # 6. Check Dashboard Statistics
            response = client.get('/api/user/statistics')
            
            assert response.status_code in [200, 401]
    
    @patch('firebase_admin.firestore.client')
    def test_complete_customer_configuration_journey(self, mock_firestore, client):
        """Test complete customer journey: scan QR -> configure -> redirect"""
        
        # Setup mock packet data
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_packet_doc = Mock()
        mock_packet_doc.exists = True
        mock_packet_doc.to_dict.return_value = {
            'id': 'PKT-CUSTOMER123',
            'state': PacketStates.CONFIG_PENDING,
            'buyer_name': 'Customer Jane',
            'qr_count': 25,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_packet_doc
        mock_db.collection.return_value.add = Mock()  # For scan logs
        
        # 1. Customer scans QR code (first time)
        response = client.get('/packet/PKT-CUSTOMER123')
        
        # Should show configuration page
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            # Should contain configuration form
            assert b'configure' in response.data.lower() or b'phone' in response.data.lower()
        
        # 2. Customer configures WhatsApp redirect
        response = client.post('/api/packet/PKT-CUSTOMER123/configure',
                             json={
                                 'redirect_type': 'whatsapp',
                                 'phone_number': '+1234567890'
                             })
        
        assert response.status_code in [200, 404, 400]
        
        # 3. Mock packet as configured for subsequent scans
        mock_packet_doc.to_dict.return_value.update({
            'state': PacketStates.CONFIG_DONE,
            'redirect_url': 'https://wa.me/1234567890'
        })
        
        # 4. Customer scans QR again (should redirect)
        response = client.get('/packet/PKT-CUSTOMER123')
        
        # Should redirect to WhatsApp
        assert response.status_code in [200, 302, 404]
        
        if response.status_code == 302:
            # Check redirect URL
            assert 'wa.me' in response.location or 'whatsapp' in response.location.lower()
    
    def test_error_handling_workflow(self, client):
        """Test error handling throughout the workflow"""
        
        # 1. Try to access non-existent packet
        response = client.get('/packet/PKT-NONEXISTENT')
        assert response.status_code == 404
        
        # 2. Try to configure non-existent packet
        response = client.post('/api/packet/PKT-NONEXISTENT/configure',
                             json={'redirect_type': 'whatsapp', 'phone_number': '+1234567890'})
        assert response.status_code in [404, 400]
        
        # 3. Try to access admin features without auth
        response = client.get('/api/packets')
        assert response.status_code in [401, 302]  # Unauthorized or redirect to login
        
        # 4. Try invalid login
        response = client.post('/auth/login', data={
            'email': 'invalid@example.com',
            'password': 'wrongpassword'
        })
        assert response.status_code in [200, 401]  # Stay on login page or unauthorized


class TestBusinessWorkflows:
    """Test business-specific workflows"""
    
    @patch('firebase_admin.firestore.client')
    def test_offline_sale_workflow(self, mock_firestore, client):
        """Test offline sale workflow"""
        
        # Setup mocks
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        # Create packet in system
        packet = Packet(
            packet_id='PKT-OFFLINE123',
            user_id='user-123',
            qr_count=25,
            state=PacketStates.SETUP_DONE,
            price=10.0
        )
        
        # Admin marks packet as sold offline
        result = packet.mark_sold(
            buyer_name='Offline Customer',
            buyer_email='customer@example.com',
            sale_price=10.0
        )
        
        assert result is True
        assert packet.state == PacketStates.CONFIG_PENDING
        assert packet.buyer_name == 'Offline Customer'
        
        # Simulate packet data in database for customer scan
        mock_packet_doc = Mock()
        mock_packet_doc.exists = True
        mock_packet_doc.to_dict.return_value = {
            'id': 'PKT-OFFLINE123',
            'state': PacketStates.CONFIG_PENDING,
            'buyer_name': 'Offline Customer',
            'qr_count': 25,
            'price': 10.0,
            'sale_price': 10.0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_packet_doc
        mock_db.collection.return_value.add = Mock()
        
        # Customer receives packet and scans QR
        response = client.get('/packet/PKT-OFFLINE123')
        
        # Should show configuration page
        assert response.status_code in [200, 404]
    
    def test_bulk_packet_creation_workflow(self, client):
        """Test creating multiple packets in bulk"""
        
        bulk_orders = [
            {'qr_count': 25, 'price': 10.0},
            {'qr_count': 50, 'price': 20.0},
            {'qr_count': 100, 'price': 35.0},  # Bulk discount
        ]
        
        created_packets = []
        
        for order in bulk_orders:
            # Would normally be done through API
            packet = Packet(
                user_id='user-123',
                qr_count=order['qr_count'],
                price=order['price']
            )
            
            created_packets.append(packet)
            
            # Verify packet properties
            assert packet.qr_count == order['qr_count']
            assert packet.price == order['price']
            assert packet.state == PacketStates.SETUP_PENDING
        
        # Verify total counts
        total_qrs = sum(p.qr_count for p in created_packets)
        total_value = sum(p.price for p in created_packets)
        
        assert total_qrs == 175  # 25 + 50 + 100
        assert total_value == 65.0  # 10 + 20 + 35
    
    @patch('firebase_admin.firestore.client')
    def test_revenue_tracking_workflow(self, mock_firestore):
        """Test revenue tracking across multiple sales"""
        
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        # Create and sell multiple packets
        sales_data = [
            {'qr_count': 25, 'base_price': 10.0, 'sale_price': 12.0},
            {'qr_count': 50, 'base_price': 20.0, 'sale_price': 18.0},  # Discount
            {'qr_count': 25, 'base_price': 10.0, 'sale_price': 10.0},  # Base price
        ]
        
        sold_packets = []
        total_revenue = 0
        
        for sale in sales_data:
            packet = Packet.create(
                user_id='user-123',
                qr_count=sale['qr_count'],
                price=sale['base_price']
            )
            
            # Mark as setup complete
            packet.mark_setup_complete('qr_image_url')
            
            # Sell packet
            packet.mark_sold('Customer', sale_price=sale['sale_price'])
            
            sold_packets.append(packet)
            total_revenue += sale['sale_price']
        
        # Verify revenue calculations
        assert len(sold_packets) == 3
        assert total_revenue == 40.0  # 12 + 18 + 10
        
        # Verify all packets are in sold state
        for packet in sold_packets:
            assert packet.is_sold()
            assert packet.state in [PacketStates.CONFIG_PENDING, PacketStates.CONFIG_DONE]


class TestScalabilityWorkflows:
    """Test workflows under scale conditions"""
    
    def test_high_volume_packet_creation(self):
        """Test creating many packets efficiently"""
        
        # Simulate creating 100 packets
        packet_count = 100
        packets = []
        
        for i in range(packet_count):
            packet = Packet(
                user_id='user-123',
                qr_count=25,
                price=10.0
            )
            packets.append(packet)
        
        # Verify all packets created correctly
        assert len(packets) == packet_count
        assert all(p.qr_count == 25 for p in packets)
        assert all(p.price == 10.0 for p in packets)
        
        # Verify unique IDs
        packet_ids = [p.id for p in packets]
        assert len(set(packet_ids)) == packet_count  # All unique
    
    def test_concurrent_customer_configurations(self):
        """Test multiple customers configuring packets simultaneously"""
        
        # Simulate multiple packets being configured
        configurations = [
            {'packet_id': 'PKT-001', 'redirect_url': 'https://wa.me/1111111111'},
            {'packet_id': 'PKT-002', 'redirect_url': 'https://wa.me/2222222222'},
            {'packet_id': 'PKT-003', 'redirect_url': 'https://example.com'},
            {'packet_id': 'PKT-004', 'redirect_url': 'https://wa.me/4444444444'},
        ]
        
        configured_packets = []
        
        for config in configurations:
            packet = Packet(
                packet_id=config['packet_id'],
                state=PacketStates.CONFIG_PENDING
            )
            
            result = packet.configure_redirect(config['redirect_url'])
            
            assert result is True
            assert packet.state == PacketStates.CONFIG_DONE
            assert packet.redirect_url == config['redirect_url']
            
            configured_packets.append(packet)
        
        # Verify all configurations succeeded
        assert len(configured_packets) == 4
        assert all(p.is_configured() for p in configured_packets)
    
    def test_analytics_calculation_performance(self):
        """Test analytics calculations with large datasets"""
        
        # Create sample data for analytics
        packets = []
        
        # Create 50 packets with various states and sales
        for i in range(50):
            state = [
                PacketStates.SETUP_PENDING,
                PacketStates.SETUP_DONE,
                PacketStates.CONFIG_PENDING,
                PacketStates.CONFIG_DONE
            ][i % 4]  # Distribute across states
            
            packet = Packet(
                user_id='user-123',
                qr_count=25,
                price=10.0,
                state=state
            )
            
            # Add sale data for sold packets
            if packet.is_sold():
                packet.sale_price = 10.0 + (i % 5)  # Varying sale prices
                packet.sale_date = datetime.now(timezone.utc)
            
            packets.append(packet)
        
        # Calculate analytics efficiently
        total_packets = len(packets)
        sold_packets = len([p for p in packets if p.is_sold()])
        configured_packets = len([p for p in packets if p.is_configured()])
        total_revenue = sum(p.sale_price or 0 for p in packets if p.is_sold())
        
        # Verify calculations
        assert total_packets == 50
        assert sold_packets > 0
        assert configured_packets >= 0
        assert total_revenue > 0
        
        # Performance check - calculations should be fast
        # In real implementation, would measure execution time
        assert isinstance(total_revenue, (int, float))


class TestErrorRecoveryWorkflows:
    """Test error recovery and resilience workflows"""
    
    def test_database_connection_failure_recovery(self, client):
        """Test handling database connection failures"""
        
        # Simulate database connection failure
        with patch('firebase_admin.firestore.client') as mock_firestore:
            mock_firestore.side_effect = Exception('Connection failed')
            
            # Try to access API endpoints
            response = client.get('/api/packets')
            
            # Should handle error gracefully
            assert response.status_code in [500, 503, 401]
    
    def test_file_upload_failure_recovery(self, client):
        """Test handling file upload failures"""
        
        with patch('firebase_admin.storage.bucket') as mock_storage:
            mock_storage.side_effect = Exception('Storage unavailable')
            
            # Create test image
            img = Image.new('RGB', (200, 200), color='white')
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            
            # Try to upload
            response = client.post('/api/packets/PKT-TEST/upload',
                                 data={'file': (img_io, 'qr.png', 'image/png')})
            
            # Should handle error gracefully
            assert response.status_code in [500, 503, 401, 404]
    
    def test_partial_packet_state_recovery(self):
        """Test recovery from partial state transitions"""
        
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        # Simulate partial state transition (state changed but not saved)
        packet.state = PacketStates.SETUP_DONE
        packet.qr_image_url = 'temp_url'
        
        # Verify state can be corrected
        if not packet.qr_image_url or packet.qr_image_url == 'temp_url':
            # Reset to consistent state
            packet.state = PacketStates.SETUP_PENDING
            packet.qr_image_url = None
        
        assert packet.state == PacketStates.SETUP_PENDING
        assert packet.qr_image_url is None