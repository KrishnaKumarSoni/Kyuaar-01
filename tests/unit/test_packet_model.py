"""
Unit tests for Packet model and state transitions
Tests packet lifecycle, business logic, and data management
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from models.packet import Packet, PacketStates


class TestPacketModel:
    """Test Packet model basic functionality"""
    
    def test_packet_creation_defaults(self):
        """Test packet creation with default values"""
        packet = Packet(user_id='user-123')
        
        assert packet.user_id == 'user-123'
        assert packet.qr_count == 25
        assert packet.state == PacketStates.SETUP_PENDING
        assert packet.config_state == 'pending'
        assert packet.price == 0.0
        assert packet.id.startswith('PKT-')
        assert packet.base_url == f"https://kyuaar.com/packet/{packet.id}"
        assert isinstance(packet.created_at, datetime)
        assert isinstance(packet.updated_at, datetime)
    
    def test_packet_creation_custom_values(self):
        """Test packet creation with custom values"""
        created_at = datetime.now(timezone.utc)
        
        packet = Packet(
            packet_id='PKT-CUSTOM123',
            user_id='user-456',
            qr_count=50,
            state=PacketStates.SETUP_DONE,
            price=20.0,
            created_at=created_at
        )
        
        assert packet.id == 'PKT-CUSTOM123'
        assert packet.user_id == 'user-456'
        assert packet.qr_count == 50
        assert packet.state == PacketStates.SETUP_DONE
        assert packet.price == 20.0
        assert packet.created_at == created_at
    
    def test_generate_packet_id(self):
        """Test packet ID generation"""
        packet_id = Packet._generate_packet_id()
        
        assert packet_id.startswith('PKT-')
        assert len(packet_id) == 12  # PKT- + 8 hex characters
        
        # Generate multiple IDs to ensure uniqueness
        ids = [Packet._generate_packet_id() for _ in range(10)]
        assert len(set(ids)) == 10  # All unique
    
    def test_calculate_price(self):
        """Test price calculation based on QR count"""
        packet = Packet(qr_count=25)
        
        # Default price per QR ($0.40)
        assert packet.calculate_price() == 10.0
        
        # Custom price per QR
        assert packet.calculate_price(price_per_qr=0.50) == 12.5
        
        # Different QR count
        packet.qr_count = 100
        assert packet.calculate_price() == 40.0


class TestPacketStates:
    """Test packet state constants and validation"""
    
    def test_packet_states_constants(self):
        """Test that all packet states are defined"""
        assert PacketStates.SETUP_PENDING == 'setup_pending'
        assert PacketStates.SETUP_DONE == 'setup_done'
        assert PacketStates.CONFIG_PENDING == 'config_pending'
        assert PacketStates.CONFIG_DONE == 'config_done'
        
        assert len(PacketStates.ALL_STATES) == 4
        assert all(state in PacketStates.ALL_STATES for state in [
            PacketStates.SETUP_PENDING,
            PacketStates.SETUP_DONE,
            PacketStates.CONFIG_PENDING,
            PacketStates.CONFIG_DONE
        ])
    
    def test_state_transitions(self):
        """Test valid state transitions are defined"""
        transitions = PacketStates.TRANSITIONS
        
        # Setup pending can only go to setup done
        assert transitions[PacketStates.SETUP_PENDING] == [PacketStates.SETUP_DONE]
        
        # Setup done can only go to config pending
        assert transitions[PacketStates.SETUP_DONE] == [PacketStates.CONFIG_PENDING]
        
        # Config pending can only go to config done
        assert transitions[PacketStates.CONFIG_PENDING] == [PacketStates.CONFIG_DONE]
        
        # Config done can go back to config pending (for reconfiguration)
        assert transitions[PacketStates.CONFIG_DONE] == [PacketStates.CONFIG_PENDING]


class TestPacketStateTransitions:
    """Test packet state transition logic"""
    
    def test_can_transition_to_valid(self):
        """Test valid state transitions"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        assert packet.can_transition_to(PacketStates.SETUP_DONE) is True
        assert packet.can_transition_to(PacketStates.CONFIG_PENDING) is False
        assert packet.can_transition_to(PacketStates.CONFIG_DONE) is False
    
    def test_can_transition_to_invalid_state(self):
        """Test transition to invalid state"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        assert packet.can_transition_to('invalid_state') is False
    
    def test_transition_to_valid(self):
        """Test successful state transition"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        old_updated = packet.updated_at
        
        result = packet.transition_to(PacketStates.SETUP_DONE)
        
        assert result is True
        assert packet.state == PacketStates.SETUP_DONE
        assert packet.updated_at > old_updated
    
    def test_transition_to_invalid(self):
        """Test failed state transition"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        original_state = packet.state
        
        result = packet.transition_to(PacketStates.CONFIG_DONE)
        
        assert result is False
        assert packet.state == original_state
    
    def test_mark_setup_complete(self):
        """Test marking packet setup as complete"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        image_url = 'https://storage.googleapis.com/bucket/qr-image.png'
        
        result = packet.mark_setup_complete(image_url)
        
        assert result is True
        assert packet.state == PacketStates.SETUP_DONE
        assert packet.qr_image_url == image_url
    
    def test_mark_setup_complete_invalid_state(self):
        """Test marking setup complete from invalid state"""
        packet = Packet(state=PacketStates.CONFIG_PENDING)
        
        result = packet.mark_setup_complete('image_url')
        
        assert result is False
        assert packet.state == PacketStates.CONFIG_PENDING
        assert packet.qr_image_url is None
    
    def test_mark_sold(self):
        """Test marking packet as sold"""
        packet = Packet(state=PacketStates.SETUP_DONE, price=10.0)
        
        result = packet.mark_sold(
            buyer_name='John Doe',
            buyer_email='john@example.com',
            sale_price=15.0
        )
        
        assert result is True
        assert packet.state == PacketStates.CONFIG_PENDING
        assert packet.buyer_name == 'John Doe'
        assert packet.buyer_email == 'john@example.com'
        assert packet.sale_price == 15.0
        assert packet.config_state == 'pending'
        assert isinstance(packet.sale_date, datetime)
    
    def test_mark_sold_default_price(self):
        """Test marking packet as sold with default price"""
        packet = Packet(state=PacketStates.SETUP_DONE, price=10.0)
        
        result = packet.mark_sold(buyer_name='Jane Doe')
        
        assert result is True
        assert packet.sale_price == 10.0  # Uses packet price
    
    def test_mark_sold_invalid_state(self):
        """Test marking packet as sold from invalid state"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        result = packet.mark_sold(buyer_name='John Doe')
        
        assert result is False
        assert packet.state == PacketStates.SETUP_PENDING
        assert packet.buyer_name is None
    
    def test_configure_redirect(self):
        """Test configuring packet redirect URL"""
        packet = Packet(state=PacketStates.CONFIG_PENDING)
        redirect_url = 'https://wa.me/1234567890'
        
        result = packet.configure_redirect(redirect_url)
        
        assert result is True
        assert packet.state == PacketStates.CONFIG_DONE
        assert packet.redirect_url == redirect_url
        assert packet.config_state == 'done'
    
    def test_configure_redirect_invalid_state(self):
        """Test configuring redirect from invalid state"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        
        result = packet.configure_redirect('https://wa.me/1234567890')
        
        assert result is False
        assert packet.redirect_url is None


class TestPacketStatusChecks:
    """Test packet status checking methods"""
    
    def test_is_ready_for_sale(self):
        """Test checking if packet is ready for sale"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        assert packet.is_ready_for_sale() is False
        
        packet.state = PacketStates.SETUP_DONE
        assert packet.is_ready_for_sale() is True
        
        packet.state = PacketStates.CONFIG_PENDING
        assert packet.is_ready_for_sale() is False
    
    def test_is_sold(self):
        """Test checking if packet has been sold"""
        packet = Packet(state=PacketStates.SETUP_PENDING)
        assert packet.is_sold() is False
        
        packet.state = PacketStates.SETUP_DONE
        assert packet.is_sold() is False
        
        packet.state = PacketStates.CONFIG_PENDING
        assert packet.is_sold() is True
        
        packet.state = PacketStates.CONFIG_DONE
        assert packet.is_sold() is True
    
    def test_is_configured(self):
        """Test checking if packet is fully configured"""
        packet = Packet(state=PacketStates.CONFIG_DONE)
        assert packet.is_configured() is False  # No redirect URL
        
        packet.redirect_url = 'https://wa.me/1234567890'
        assert packet.is_configured() is True
        
        packet.state = PacketStates.CONFIG_PENDING
        assert packet.is_configured() is False  # Wrong state


class TestPacketDatabase:
    """Test packet database operations"""
    
    @patch('firebase_admin.firestore.client')
    def test_save_success(self, mock_firestore):
        """Test successful packet save"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        packet = Packet(user_id='user-123')
        result = packet.save()
        
        assert result is True
        mock_document.set.assert_called_once()
    
    @patch('firebase_admin.firestore.client')
    def test_save_failure(self, mock_firestore):
        """Test packet save failure"""
        # Mock Firestore to raise exception
        mock_firestore.side_effect = Exception('Database error')
        
        packet = Packet(user_id='user-123')
        result = packet.save()
        
        assert result is False
    
    @patch('firebase_admin.firestore.client')
    def test_get_by_id_found(self, mock_firestore):
        """Test getting packet by ID when found"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        mock_doc = Mock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            'id': 'PKT-12345',
            'user_id': 'user-123',
            'qr_count': 25,
            'state': PacketStates.SETUP_PENDING,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        mock_document.get.return_value = mock_doc
        
        packet = Packet.get_by_id('PKT-12345')
        
        assert packet is not None
        assert packet.id == 'PKT-12345'
        assert packet.user_id == 'user-123'
    
    @patch('firebase_admin.firestore.client')
    def test_get_by_id_not_found(self, mock_firestore):
        """Test getting packet by ID when not found"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        mock_doc = Mock()
        mock_doc.exists = False
        mock_document.get.return_value = mock_doc
        
        packet = Packet.get_by_id('PKT-NONEXISTENT')
        
        assert packet is None
    
    @patch('firebase_admin.firestore.client')
    def test_get_by_user(self, mock_firestore):
        """Test getting packets by user"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_query = Mock()
        mock_collection.where.return_value = mock_query
        
        # Mock documents
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {
            'id': 'PKT-1',
            'user_id': 'user-123',
            'qr_count': 25,
            'state': PacketStates.SETUP_PENDING,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {
            'id': 'PKT-2',
            'user_id': 'user-123',
            'qr_count': 50,
            'state': PacketStates.SETUP_DONE,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        mock_query.stream.return_value = [mock_doc1, mock_doc2]
        
        packets = Packet.get_by_user('user-123')
        
        assert len(packets) == 2
        assert packets[0].id == 'PKT-1'
        assert packets[1].id == 'PKT-2'
        assert all(p.user_id == 'user-123' for p in packets)
    
    @patch('firebase_admin.firestore.client')
    def test_count_by_user(self, mock_firestore):
        """Test counting packets by user"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_query = Mock()
        mock_collection.where.return_value = mock_query
        
        # Mock 3 documents
        mock_docs = [Mock(), Mock(), Mock()]
        mock_query.stream.return_value = mock_docs
        
        count = Packet.count_by_user('user-123')
        
        assert count == 3
    
    @patch('firebase_admin.firestore.client')
    def test_count_by_user_with_state(self, mock_firestore):
        """Test counting packets by user and state"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_query = Mock()
        mock_collection.where.return_value = mock_query
        
        # Mock 2 documents for specific state
        mock_docs = [Mock(), Mock()]
        mock_query.stream.return_value = mock_docs
        
        count = Packet.count_by_user('user-123', state=PacketStates.SETUP_DONE)
        
        assert count == 2
        # Verify state filter was applied
        assert mock_collection.where.call_count == 2  # user_id and state
    
    @patch('firebase_admin.firestore.client')
    def test_create_packet(self, mock_firestore):
        """Test creating new packet"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        packet = Packet.create(user_id='user-123', qr_count=50, price=20.0)
        
        assert packet is not None
        assert packet.user_id == 'user-123'
        assert packet.qr_count == 50
        assert packet.price == 20.0
        assert packet.state == PacketStates.SETUP_PENDING
    
    @patch('firebase_admin.firestore.client')
    def test_create_packet_default_price(self, mock_firestore):
        """Test creating packet with default price calculation"""
        # Mock Firestore
        mock_db = Mock()
        mock_firestore.return_value = mock_db
        
        mock_collection = Mock()
        mock_db.collection.return_value = mock_collection
        
        mock_document = Mock()
        mock_collection.document.return_value = mock_document
        
        packet = Packet.create(user_id='user-123', qr_count=25)
        
        assert packet is not None
        assert packet.price == 10.0  # 25 * $0.40


class TestPacketDataSerialization:
    """Test packet data serialization and deserialization"""
    
    def test_to_dict(self):
        """Test converting packet to dictionary"""
        created_at = datetime.now(timezone.utc)
        sale_date = datetime.now(timezone.utc)
        
        packet = Packet(
            packet_id='PKT-12345',
            user_id='user-123',
            qr_count=25,
            state=PacketStates.SETUP_DONE,
            price=10.0,
            qr_image_url='https://example.com/qr.png',
            buyer_name='John Doe',
            sale_price=15.0,
            sale_date=sale_date,
            created_at=created_at
        )
        
        data = packet.to_dict()
        
        assert data['id'] == 'PKT-12345'
        assert data['user_id'] == 'user-123'
        assert data['qr_count'] == 25
        assert data['state'] == PacketStates.SETUP_DONE
        assert data['price'] == 10.0
        assert data['qr_image_url'] == 'https://example.com/qr.png'
        assert data['buyer_name'] == 'John Doe'
        assert data['sale_price'] == 15.0
        assert data['sale_date'] == sale_date.isoformat()
        assert data['created_at'] == created_at.isoformat()
    
    def test_from_dict(self):
        """Test creating packet from dictionary"""
        created_at = datetime.now(timezone.utc)
        
        data = {
            'id': 'PKT-12345',
            'user_id': 'user-123',
            'qr_count': 25,
            'state': PacketStates.SETUP_DONE,
            'price': 10.0,
            'qr_image_url': 'https://example.com/qr.png',
            'created_at': created_at.isoformat()
        }
        
        packet = Packet.from_dict(data)
        
        assert packet.id == 'PKT-12345'
        assert packet.user_id == 'user-123'
        assert packet.qr_count == 25
        assert packet.state == PacketStates.SETUP_DONE
        assert packet.price == 10.0
        assert packet.qr_image_url == 'https://example.com/qr.png'
        assert packet.created_at == created_at
    
    def test_from_dict_with_none_values(self):
        """Test creating packet from dictionary with None values"""
        data = {
            'id': 'PKT-12345',
            'user_id': 'user-123',
            'created_at': None,
            'updated_at': None,
            'sale_date': None
        }
        
        packet = Packet.from_dict(data)
        
        assert packet.id == 'PKT-12345'
        assert packet.user_id == 'user-123'
        assert packet.created_at is None
        assert packet.updated_at is None
        assert packet.sale_date is None