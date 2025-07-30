"""
Integration tests for complete packet lifecycle
Tests end-to-end packet workflows and state transitions
"""

import pytest
import json
import io
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from models.packet import Packet, PacketStates
from models.user import User


class TestPacketLifecycleIntegration:
    """Test complete packet lifecycle from creation to configuration"""
    
    @patch('firebase_admin.firestore.client')
    def test_complete_packet_lifecycle(self, mock_firestore):
        """Test complete packet workflow from creation to configuration"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        # 1. Create packet
        packet = Packet.create(user_id='user-123', qr_count=25, price=10.0)
        
        assert packet is not None
        assert packet.state == PacketStates.SETUP_PENDING
        assert packet.qr_count == 25
        assert packet.price == 10.0
        
        # 2. Upload QR image (mark setup complete)
        qr_image_url = 'https://storage.googleapis.com/bucket/qr-image.png'
        result = packet.mark_setup_complete(qr_image_url)
        
        assert result is True
        assert packet.state == PacketStates.SETUP_DONE
        assert packet.qr_image_url == qr_image_url
        assert packet.is_ready_for_sale() is True
        
        # 3. Mark packet as sold
        result = packet.mark_sold(
            buyer_name='John Doe',
            buyer_email='john@example.com',
            sale_price=12.0
        )
        
        assert result is True
        assert packet.state == PacketStates.CONFIG_PENDING
        assert packet.buyer_name == 'John Doe'
        assert packet.buyer_email == 'john@example.com'
        assert packet.sale_price == 12.0
        assert packet.is_sold() is True
        assert isinstance(packet.sale_date, datetime)
        
        # 4. Configure redirect URL
        redirect_url = 'https://wa.me/1234567890'
        result = packet.configure_redirect(redirect_url)
        
        assert result is True
        assert packet.state == PacketStates.CONFIG_DONE
        assert packet.redirect_url == redirect_url
        assert packet.is_configured() is True
        
        # 5. Verify final state
        assert packet.config_state == 'done'
        assert packet.is_sold() is True
        assert packet.is_configured() is True
    
    @patch('firebase_admin.firestore.client')
    def test_packet_reconfiguration(self, mock_firestore):
        """Test packet reconfiguration after initial setup"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        # Create and configure packet
        packet = Packet.create(user_id='user-123')
        packet.mark_setup_complete('qr_image.png')
        packet.mark_sold('John Doe', sale_price=10.0)
        packet.configure_redirect('https://wa.me/1111111111')
        
        assert packet.state == PacketStates.CONFIG_DONE
        assert packet.redirect_url == 'https://wa.me/1111111111'
        
        # Reconfigure with new redirect
        packet.state = PacketStates.CONFIG_PENDING  # Simulate reconfiguration state
        result = packet.configure_redirect('https://wa.me/2222222222')
        
        assert result is True
        assert packet.state == PacketStates.CONFIG_DONE
        assert packet.redirect_url == 'https://wa.me/2222222222'
    
    def test_invalid_state_transitions(self):
        """Test that invalid state transitions are blocked"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        # Cannot skip setup_done state
        result = packet.transition_to(PacketStates.CONFIG_PENDING)
        assert result is False
        assert packet.state == PacketStates.SETUP_PENDING
        
        # Cannot go directly to config_done
        result = packet.transition_to(PacketStates.CONFIG_DONE)
        assert result is False
        assert packet.state == PacketStates.SETUP_PENDING
        
        # Cannot configure redirect without being sold
        result = packet.configure_redirect('https://wa.me/1234567890')
        assert result is False
        assert packet.redirect_url is None
    
    def test_packet_business_rules(self):
        """Test business rules are enforced"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        # Cannot sell packet that isn't setup
        result = packet.mark_sold('Buyer Name')
        assert result is False
        
        # Cannot configure without being sold first
        packet.state = PacketStates.SETUP_DONE
        result = packet.configure_redirect('https://wa.me/1234567890')
        assert result is False
        
        # Must have QR image to complete setup
        assert packet.qr_image_url is None
        packet.state = PacketStates.SETUP_PENDING
        result = packet.mark_setup_complete('image_url')
        assert result is True
        assert packet.qr_image_url == 'image_url'


class TestPacketDatabaseIntegration:
    """Test packet database operations integration"""
    
    @patch('firebase_admin.firestore.client')
    def test_packet_crud_operations(self, mock_firestore):
        """Test complete CRUD operations for packets"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        # Create packet
        packet = Packet.create(user_id='user-123', qr_count=25, price=10.0)
        assert packet is not None
        
        # Update packet
        result = packet.update(qr_count=50, price=20.0)
        assert result is True
        assert packet.qr_count == 50
        assert packet.price == 20.0
        
        # Verify save was called
        mock_document.set.assert_called()
    
    @patch('firebase_admin.firestore.client')
    def test_packet_query_operations(self, mock_firestore):
        """Test packet querying operations"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        # Mock query for get_by_user
        mock_query = Mock()
        mock_collection.where.return_value = mock_query
        
        # Mock documents
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {
            'id': 'PKT-1',
            'user_id': 'user-123',
            'state': PacketStates.SETUP_DONE,
            'qr_count': 25,
            'price': 10.0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {
            'id': 'PKT-2',
            'user_id': 'user-123',
            'state': PacketStates.CONFIG_DONE,
            'qr_count': 50,
            'price': 20.0,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        
        # Test get_by_user
        packets = Packet.get_by_user('user-123')
        
        assert len(packets) == 2
        assert all(p.user_id == 'user-123' for p in packets)
        assert packets[0].state == PacketStates.SETUP_DONE
        assert packets[1].state == PacketStates.CONFIG_DONE
        
        # Test count_by_user with state filter
        mock_query.stream.return_value = [mock_doc2]  # Only config_done packet
        count = Packet.count_by_user('user-123', state=PacketStates.CONFIG_DONE)
        assert count == 1


class TestPacketPricingIntegration:
    """Test packet pricing calculations and business logic"""
    
    def test_pricing_calculation_scenarios(self):
        """Test various pricing calculation scenarios"""
        # Standard pricing
        packet = Packet(qr_count=25)
        assert packet.calculate_price() == 10.0  # 25 * $0.40
        
        # Bulk pricing
        packet = Packet(qr_count=100)
        assert packet.calculate_price() == 40.0  # 100 * $0.40
        
        # Custom pricing
        packet = Packet(qr_count=25)
        assert packet.calculate_price(price_per_qr=0.50) == 12.5  # 25 * $0.50
        
        # Small packet
        packet = Packet(qr_count=1)
        assert packet.calculate_price() == 0.40  # 1 * $0.40
    
    def test_packet_sale_pricing(self):
        """Test sale pricing scenarios"""
        packet = Packet(qr_count=25, price=10.0)
        
        # Sale at default price
        packet.mark_sold('Buyer', sale_price=None)
        assert packet.sale_price == 10.0
        
        # Sale at custom price
        packet = Packet(qr_count=25, price=10.0)
        packet.mark_sold('Buyer', sale_price=15.0)
        assert packet.sale_price == 15.0
        
        # Sale price different from base price
        assert packet.price == 10.0  # Base price unchanged
        assert packet.sale_price == 15.0  # Actual sale price
    
    def test_revenue_calculation(self):
        """Test revenue calculation from packets"""
        packets = [
            Packet(sale_price=10.0, state=PacketStates.CONFIG_DONE),
            Packet(sale_price=15.0, state=PacketStates.CONFIG_DONE),
            Packet(sale_price=20.0, state=PacketStates.CONFIG_PENDING),
            Packet(price=10.0, state=PacketStates.SETUP_DONE)  # Not sold
        ]
        
        # Calculate total revenue from sold packets
        sold_packets = [p for p in packets if p.is_sold()]
        total_revenue = sum(p.sale_price or 0 for p in sold_packets)
        
        assert len(sold_packets) == 3
        assert total_revenue == 45.0  # 10 + 15 + 20


class TestPacketValidationIntegration:
    """Test packet validation and error handling"""
    
    def test_packet_data_validation(self):
        """Test packet data validation"""
        # Valid packet data
        packet = Packet(
            user_id='user-123',
            qr_count=25,
            price=10.0
        )
        
        assert packet.user_id == 'user-123'
        assert packet.qr_count == 25
        assert packet.price == 10.0
        
        # Edge cases
        packet = Packet(qr_count=1, price=0.40)
        assert packet.qr_count == 1
        assert packet.price == 0.40
        
        packet = Packet(qr_count=100, price=40.0)
        assert packet.qr_count == 100
        assert packet.price == 40.0
    
    def test_packet_url_validation(self):
        """Test packet URL generation and validation"""
        packet = Packet(packet_id='PKT-TEST123')
        
        assert packet.base_url == 'https://kyuaar.com/packet/PKT-TEST123'
        
        # Test redirect URL validation would go here
        # (In a real implementation, you might validate WhatsApp URLs, etc.)
        valid_whatsapp_url = 'https://wa.me/1234567890'
        packet.configure_redirect(valid_whatsapp_url)
        
        # URLs should be stored as-is (validation would be in route handlers)
        assert packet.redirect_url == valid_whatsapp_url
    
    def test_packet_timestamp_handling(self):
        """Test packet timestamp handling"""
        packet = Packet()
        
        # Created and updated timestamps should be set
        assert isinstance(packet.created_at, datetime)
        assert isinstance(packet.updated_at, datetime)
        
        # Test state transitions update timestamp
        old_updated = packet.updated_at
        packet.transition_to(PacketStates.SETUP_DONE)
        
        assert packet.updated_at > old_updated
        
        # Test sale date is set when sold
        packet.mark_sold('Buyer')
        assert isinstance(packet.sale_date, datetime)