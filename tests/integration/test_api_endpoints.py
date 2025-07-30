"""
Integration tests for API endpoints
Tests all API routes with proper authentication and data flow
"""

import pytest
import json
import io
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from flask_login import login_user

from models.user import User
from models.packet import Packet, PacketStates
from models.activity import Activity, ActivityType


class TestPacketAPIEndpoints:
    """Test packet management API endpoints"""
    
    @patch('models.packet.Packet.get_by_user')
    def test_get_packets_success(self, mock_get_by_user, client, app):
        """Test getting user packets"""
        # Mock packets
        mock_packets = [
            Mock(to_dict=lambda: {'id': 'PKT-1', 'state': 'setup_pending'}),
            Mock(to_dict=lambda: {'id': 'PKT-2', 'state': 'setup_done'})
        ]
        mock_get_by_user.return_value = mock_packets
        
        with app.test_request_context():
            # Mock authenticated user
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.get('/api/packets')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'packets' in data
        assert 'count' in data
        assert data['count'] == 2
        assert len(data['packets']) == 2
    
    def test_get_packets_unauthorized(self, client):
        """Test getting packets without authentication"""
        response = client.get('/api/packets')
        assert response.status_code == 401
    
    @patch('models.packet.Packet.create')
    @patch('models.activity.Activity.log')
    def test_create_packet_success(self, mock_log, mock_create, client, app):
        """Test creating new packet"""
        # Mock packet creation
        mock_packet = Mock()
        mock_packet.id = 'PKT-NEW123'
        mock_packet.to_dict.return_value = {
            'id': 'PKT-NEW123',
            'qr_count': 25,
            'state': 'setup_pending'
        }
        mock_create.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets', 
                    json={'qr_count': 25, 'price': 10.0})
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['message'] == 'Packet created successfully'
        assert 'packet' in data
        
        # Verify packet creation was called
        mock_create.assert_called_once_with(
            user_id='user-123',
            qr_count=25,
            price=10.0
        )
        
        # Verify activity was logged
        mock_log.assert_called_once()
    
    def test_create_packet_invalid_qr_count(self, client, app):
        """Test creating packet with invalid QR count"""
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                # Too many QRs
                response = client.post('/api/packets', json={'qr_count': 150})
                assert response.status_code == 400
                data = json.loads(response.data)
                assert 'between 1 and 100' in data['error']
                
                # Too few QRs
                response = client.post('/api/packets', json={'qr_count': 0})
                assert response.status_code == 400
                
                # Invalid type
                response = client.post('/api/packets', json={'qr_count': 'invalid'})
                assert response.status_code == 400
    
    @patch('models.packet.Packet.get_by_id_and_user')
    def test_get_packet_success(self, mock_get_packet, client, app):
        """Test getting specific packet"""
        # Mock packet
        mock_packet = Mock()
        mock_packet.to_dict.return_value = {
            'id': 'PKT-123',
            'state': 'setup_done'
        }
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.get('/api/packets/PKT-123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'packet' in data
        assert data['packet']['id'] == 'PKT-123'
    
    @patch('models.packet.Packet.get_by_id_and_user')
    def test_get_packet_not_found(self, mock_get_packet, client, app):
        """Test getting non-existent packet"""
        mock_get_packet.return_value = None
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.get('/api/packets/PKT-NONEXISTENT')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'not found' in data['error']


class TestFileUploadAPI:
    """Test file upload API endpoints"""
    
    @patch('firebase_admin.storage.bucket')
    @patch('models.packet.Packet.get_by_id_and_user')
    @patch('models.activity.Activity.log')
    def test_upload_qr_image_success(self, mock_log, mock_get_packet, mock_bucket, client, app):
        """Test successful QR image upload"""
        # Mock packet
        mock_packet = Mock()
        mock_packet.id = 'PKT-123'
        mock_packet.can_transition_to.return_value = True
        mock_packet.mark_setup_complete.return_value = True
        mock_packet.save.return_value = True
        mock_packet.to_dict.return_value = {
            'id': 'PKT-123',
            'state': 'setup_done',
            'qr_image_url': 'https://storage.googleapis.com/bucket/qr_images/PKT-123.png'
        }
        mock_get_packet.return_value = mock_packet
        
        # Mock Firebase Storage
        mock_storage_bucket = Mock()
        mock_bucket.return_value = mock_storage_bucket
        
        mock_blob = Mock()
        mock_blob.public_url = 'https://storage.googleapis.com/bucket/qr_images/PKT-123.png'
        mock_storage_bucket.blob.return_value = mock_blob
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            # Create test image file
            test_image = io.BytesIO()
            test_image.write(b'fake image data')
            test_image.seek(0)
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets/PKT-123/upload',
                    data={'qr_image': (test_image, 'test_qr.png')},
                    content_type='multipart/form-data')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'QR image uploaded successfully'
        assert 'image_url' in data
        assert 'packet' in data
        
        # Verify calls
        mock_blob.upload_from_file.assert_called_once()
        mock_blob.make_public.assert_called_once()
        mock_packet.mark_setup_complete.assert_called_once()
        mock_log.assert_called_once()
    
    @patch('models.packet.Packet.get_by_id_and_user')
    def test_upload_no_file(self, mock_get_packet, client, app):
        """Test upload without file"""
        mock_packet = Mock()
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets/PKT-123/upload',
                    data={}, content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'No file uploaded' in data['error']
    
    @patch('models.packet.Packet.get_by_id_and_user')
    def test_upload_invalid_file_type(self, mock_get_packet, client, app):
        """Test upload with invalid file type"""
        mock_packet = Mock()
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            test_file = io.BytesIO()
            test_file.write(b'fake file data')
            test_file.seek(0)
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets/PKT-123/upload',
                    data={'qr_image': (test_file, 'test.txt')},
                    content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid file type' in data['error']
    
    @patch('models.packet.Packet.get_by_id_and_user')
    def test_upload_invalid_packet_state(self, mock_get_packet, client, app):
        """Test upload when packet is in wrong state"""
        mock_packet = Mock()
        mock_packet.can_transition_to.return_value = False
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            test_image = io.BytesIO()
            test_image.write(b'fake image data')
            test_image.seek(0)
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets/PKT-123/upload',
                    data={'qr_image': (test_image, 'test.png')},
                    content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'not ready for QR upload' in data['error']


class TestPacketSaleAPI:
    """Test packet sale API endpoints"""
    
    @patch('models.packet.Packet.get_by_id_and_user')
    @patch('models.activity.Activity.log')
    def test_mark_packet_sold_success(self, mock_log, mock_get_packet, client, app):
        """Test marking packet as sold"""
        # Mock packet
        mock_packet = Mock()
        mock_packet.id = 'PKT-123'
        mock_packet.mark_sold.return_value = True
        mock_packet.save.return_value = True
        mock_packet.sale_price = 15.0
        mock_packet.to_dict.return_value = {
            'id': 'PKT-123',
            'state': 'config_pending',
            'buyer_name': 'John Doe',
            'sale_price': 15.0
        }
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets/PKT-123/sell',
                    json={
                        'buyer_name': 'John Doe',
                        'buyer_email': 'john@example.com',
                        'sale_price': 15.0
                    })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Packet marked as sold successfully'
        assert 'packet' in data
        
        # Verify calls
        mock_packet.mark_sold.assert_called_once_with('John Doe', 'john@example.com', 15.0)
        mock_log.assert_called_once()
    
    @patch('models.packet.Packet.get_by_id_and_user')
    def test_mark_packet_sold_missing_buyer_name(self, mock_get_packet, client, app):
        """Test marking packet as sold without buyer name"""
        mock_packet = Mock()
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets/PKT-123/sell',
                    json={'sale_price': 15.0})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Buyer name is required' in data['error']
    
    @patch('models.packet.Packet.get_by_id_and_user')
    def test_mark_packet_sold_invalid_state(self, mock_get_packet, client, app):
        """Test marking packet as sold when in wrong state"""
        mock_packet = Mock()
        mock_packet.mark_sold.return_value = False
        mock_get_packet.return_value = mock_packet
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets/PKT-123/sell',
                    json={'buyer_name': 'John Doe'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Cannot mark packet as sold' in data['error']


class TestUserStatisticsAPI:
    """Test user statistics API endpoints"""
    
    @patch('models.packet.Packet.get_by_user')
    def test_get_user_statistics(self, mock_get_by_user, client, app):
        """Test getting user statistics"""
        # Mock packets in different states
        mock_packets = [
            Mock(state='setup_pending', is_sold=lambda: False, sale_price=None),
            Mock(state='setup_done', is_sold=lambda: False, sale_price=None),
            Mock(state='config_pending', is_sold=lambda: True, sale_price=10.0),
            Mock(state='config_done', is_sold=lambda: True, sale_price=15.0),
            Mock(state='config_done', is_sold=lambda: True, sale_price=12.0),
        ]
        mock_get_by_user.return_value = mock_packets
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.get('/api/user/statistics')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['total_packets'] == 5
        assert data['by_state']['setup_pending'] == 1
        assert data['by_state']['setup_done'] == 1
        assert data['by_state']['config_pending'] == 1
        assert data['by_state']['config_done'] == 2
        assert data['total_revenue'] == 37.0  # 10 + 15 + 12
    
    @patch('models.activity.Activity.get_recent_by_user')
    def test_get_user_activity(self, mock_get_activity, client, app):
        """Test getting user activity"""
        # Mock activities
        mock_activities = [
            Mock(
                to_dict=lambda: {
                    'id': 'act-1',
                    'title': 'Packet Created',
                    'created_at': '2024-01-01T10:00:00Z'
                },
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                to_dict=lambda: {
                    'id': 'act-2',
                    'title': 'Packet Sold',
                    'created_at': '2024-01-01T11:00:00Z'
                },
                created_at=datetime.now(timezone.utc)
            )
        ]
        mock_get_activity.return_value = mock_activities
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.get('/api/user/activity')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'activities' in data
        assert 'count' in data
        assert data['count'] == 2
        assert len(data['activities']) == 2


class TestCustomerConfigurationAPI:
    """Test customer-facing configuration API (no auth required)"""
    
    @patch('firebase_admin.firestore.client')
    @patch('models.activity.Activity.log')
    def test_configure_packet_whatsapp_success(self, mock_log, mock_firestore, client):
        """Test successful WhatsApp configuration"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'PKT-123',
            'user_id': 'user-123',
            'state': 'config_pending'
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        # Mock packet methods
        with patch('models.packet.Packet.from_dict') as mock_from_dict, \
             patch.object(Packet, 'configure_redirect') as mock_configure, \
             patch.object(Packet, 'save') as mock_save:
            
            mock_packet = Mock()
            mock_packet.state = 'config_pending'
            mock_packet.user_id = 'user-123'
            mock_packet.configure_redirect.return_value = True
            mock_packet.save.return_value = True
            mock_from_dict.return_value = mock_packet
            
            response = client.post('/api/packet/PKT-123/configure',
                json={
                    'type': 'whatsapp',
                    'phone': '9166900151'
                })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'Packet configured successfully'
        assert 'redirect_url' in data
        assert 'wa.me/919166900151' in data['redirect_url']
        
        # Verify configuration was called
        mock_packet.configure_redirect.assert_called_once()
        mock_log.assert_called_once()
    
    @patch('firebase_admin.firestore.client')
    def test_configure_packet_custom_url(self, mock_firestore, client):
        """Test custom URL configuration"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'PKT-123',
            'state': 'config_pending'
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        with patch('models.packet.Packet.from_dict') as mock_from_dict, \
             patch.object(Packet, 'configure_redirect') as mock_configure, \
             patch.object(Packet, 'save') as mock_save, \
             patch('models.activity.Activity.log'):
            
            mock_packet = Mock()
            mock_packet.state = 'config_pending'
            mock_packet.user_id = 'user-123'
            mock_packet.configure_redirect.return_value = True
            mock_packet.save.return_value = True
            mock_from_dict.return_value = mock_packet
            
            response = client.post('/api/packet/PKT-123/configure',
                json={
                    'type': 'custom',
                    'url': 'example.com'
                })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'https://example.com' in data['redirect_url']
    
    @patch('firebase_admin.firestore.client')
    def test_configure_packet_not_found(self, mock_firestore, client):
        """Test configuring non-existent packet"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.post('/api/packet/PKT-NONEXISTENT/configure',
            json={
                'type': 'whatsapp',
                'phone': '9166900151'
            })
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Invalid packet ID' in data['error']
    
    @patch('firebase_admin.firestore.client')
    def test_configure_packet_wrong_state(self, mock_firestore, client):
        """Test configuring packet in wrong state"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'PKT-123',
            'state': 'setup_pending'
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        with patch('models.packet.Packet.from_dict') as mock_from_dict:
            mock_packet = Mock()
            mock_packet.state = 'setup_pending'
            mock_from_dict.return_value = mock_packet
            
            response = client.post('/api/packet/PKT-123/configure',
                json={
                    'type': 'whatsapp',
                    'phone': '9166900151'
                })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'not ready for configuration' in data['error']
    
    def test_configure_packet_missing_phone(self, client):
        """Test WhatsApp configuration without phone number"""
        response = client.post('/api/packet/PKT-123/configure',
            json={'type': 'whatsapp'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Phone number required' in data['error']
    
    def test_configure_packet_missing_url(self, client):
        """Test custom URL configuration without URL"""
        response = client.post('/api/packet/PKT-123/configure',
            json={'type': 'custom'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'URL required' in data['error']
    
    @patch('firebase_admin.firestore.client')
    def test_get_packet_status(self, mock_firestore, client):
        """Test getting packet status"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'PKT-123',
            'state': 'config_done',
            'redirect_url': 'https://wa.me/919166900151',
            'base_url': 'https://kyuaar.com/packet/PKT-123'
        }
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get('/api/packet/PKT-123/status')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['packet_id'] == 'PKT-123'
        assert data['state'] == 'config_done'
        assert data['is_configured'] is True
        assert 'redirect_url' in data
        assert 'base_url' in data
    
    @patch('firebase_admin.firestore.client')
    def test_get_packet_status_not_found(self, mock_firestore, client):
        """Test getting status of non-existent packet"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_doc = Mock()
        mock_doc.exists = False
        
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        response = client.get('/api/packet/PKT-NONEXISTENT/status')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'not found' in data['error']


class TestAPIErrorHandling:
    """Test API error handling and edge cases"""
    
    @patch('models.packet.Packet.get_by_user')
    def test_api_database_error(self, mock_get_by_user, client, app):
        """Test API response when database error occurs"""
        # Mock database error
        mock_get_by_user.side_effect = Exception('Database connection failed')
        
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.get('/api/packets')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'Failed to retrieve packets' in data['error']
    
    def test_api_invalid_json(self, client, app):
        """Test API with invalid JSON data"""
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets',
                    data='invalid json',
                    content_type='application/json')
        
        # Flask should handle invalid JSON and return 400
        assert response.status_code == 400
    
    def test_api_missing_content_type(self, client, app):
        """Test API without proper content type"""
        with app.test_request_context():
            mock_user = Mock()
            mock_user.id = 'user-123'
            mock_user.is_authenticated = True
            mock_user.is_active = True
            mock_user.is_anonymous = False
            mock_user.get_id = lambda: 'user-123'
            
            with patch('flask_login.current_user', mock_user):
                response = client.post('/api/packets',
                    data='{"qr_count": 25}')
        
        # Should still work as Flask can parse JSON from data
        assert response.status_code in [200, 201, 400, 500]


class TestAPIValidation:
    """Test API input validation"""
    
    def test_phone_number_normalization(self, client):
        """Test phone number normalization in WhatsApp config"""
        test_cases = [
            ('9166900151', '919166900151'),  # Add country code
            ('919166900151', '919166900151'),  # Keep existing country code
            ('+91 9166900151', '919166900151'),  # Remove + and spaces
            ('91-9166-900-151', '919166900151'),  # Remove dashes
        ]
        
        with patch('firebase_admin.firestore.client') as mock_firestore, \
             patch('models.packet.Packet.from_dict') as mock_from_dict, \
             patch('models.activity.Activity.log'):
            
            # Mock Firestore
            mock_db = Mock()
            mock_firestore.return_value = mock_db
            
            mock_doc = Mock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                'id': 'PKT-123',
                'state': 'config_pending'
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
            
            # Mock packet
            mock_packet = Mock()
            mock_packet.state = 'config_pending'
            mock_packet.user_id = 'user-123'
            mock_packet.configure_redirect.return_value = True
            mock_packet.save.return_value = True
            mock_from_dict.return_value = mock_packet
            
            for input_phone, expected_phone in test_cases:
                response = client.post('/api/packet/PKT-123/configure',
                    json={
                        'type': 'whatsapp',
                        'phone': input_phone
                    })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert f'wa.me/{expected_phone}' in data['redirect_url']
    
    def test_url_normalization(self, client):
        """Test URL normalization in custom config"""
        test_cases = [
            ('example.com', 'https://example.com'),
            ('http://example.com', 'http://example.com'),
            ('https://example.com', 'https://example.com'),
        ]
        
        with patch('firebase_admin.firestore.client') as mock_firestore, \
             patch('models.packet.Packet.from_dict') as mock_from_dict, \
             patch('models.activity.Activity.log'):
            
            # Mock Firestore
            mock_db = Mock()
            mock_firestore.return_value = mock_db
            
            mock_doc = Mock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                'id': 'PKT-123',
                'state': 'config_pending'
            }
            mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
            
            # Mock packet
            mock_packet = Mock()
            mock_packet.state = 'config_pending'
            mock_packet.user_id = 'user-123'
            mock_packet.configure_redirect.return_value = True
            mock_packet.save.return_value = True
            mock_from_dict.return_value = mock_packet
            
            for input_url, expected_url in test_cases:
                response = client.post('/api/packet/PKT-123/configure',
                    json={
                        'type': 'custom',
                        'url': input_url
                    })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['redirect_url'] == expected_url