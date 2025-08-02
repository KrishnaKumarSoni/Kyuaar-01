"""
Packet model for Kyuaar QR code packet management
Handles packet lifecycle, state transitions, and business logic
"""

import uuid
from datetime import datetime, timezone
from firebase_admin import firestore
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PacketStates:
    """Constants for packet states"""
    SETUP_DONE = 'setup_done'
    CONFIG_PENDING = 'config_pending'
    CONFIG_DONE = 'config_done'
    
    ALL_STATES = [SETUP_DONE, CONFIG_PENDING, CONFIG_DONE]
    
    # Valid state transitions
    TRANSITIONS = {
        SETUP_DONE: [CONFIG_PENDING],
        CONFIG_PENDING: [CONFIG_DONE],
        CONFIG_DONE: [CONFIG_PENDING]  # Allow reconfiguration
    }


class Packet:
    """Packet model representing a QR code packet"""
    
    def __init__(self, packet_id: str = None, user_id: str = None, qr_count: int = 25,
                 state: str = PacketStates.SETUP_DONE, config_state: str = 'pending',
                 price: float = 0.0, base_url: str = None, qr_image_url: str = None,
                 redirect_url: str = None, buyer_name: str = None, buyer_email: str = None,
                 sale_price: float = None, sale_date: datetime = None,
                 created_at: datetime = None, updated_at: datetime = None, deleted: bool = False,
                 master_id: str = None, master_qr_url: str = None, packet_password: str = None):
        
        self.id = packet_id or self._generate_packet_id()
        self.user_id = user_id
        self.qr_count = qr_count
        self.state = state
        self.config_state = config_state
        self.price = price
        self.base_url = base_url or f"https://kyuaar.com/packet/{self.id}"
        self.qr_image_url = qr_image_url
        self.redirect_url = redirect_url
        self.buyer_name = buyer_name
        self.buyer_email = buyer_email
        self.sale_price = sale_price
        self.sale_date = sale_date
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.deleted = deleted
        self.master_id = master_id or self._generate_master_id()
        self.master_qr_url = master_qr_url
        self.packet_password = packet_password or self._generate_password()
    
    @staticmethod
    def _generate_packet_id() -> str:
        """Generate unique packet ID"""
        return f"PKT-{uuid.uuid4().hex[:8].upper()}"
    
    @staticmethod
    def _generate_master_id() -> str:
        """Generate unique master ID (unrelated to packet ID)"""
        return f"MGT-{uuid.uuid4().hex[:10].upper()}"
    
    @staticmethod
    def _generate_password() -> str:
        """Generate packet password for admin support"""
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(6))
    
    def can_transition_to(self, new_state: str) -> bool:
        """Check if packet can transition to new state"""
        if new_state not in PacketStates.ALL_STATES:
            return False
        
        allowed_states = PacketStates.TRANSITIONS.get(self.state, [])
        return new_state in allowed_states
    
    def transition_to(self, new_state: str) -> bool:
        """Transition packet to new state if valid"""
        if not self.can_transition_to(new_state):
            logger.warning(f"Invalid state transition from {self.state} to {new_state} for packet {self.id}")
            return False
        
        old_state = self.state
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Packet {self.id} transitioned from {old_state} to {new_state}")
        return True
    
    def mark_setup_complete(self, qr_image_url: str) -> bool:
        """Mark packet setup as complete with QR image"""
        if not self.can_transition_to(PacketStates.SETUP_DONE):
            return False
        
        self.qr_image_url = qr_image_url
        return self.transition_to(PacketStates.SETUP_DONE)
    
    def mark_sold(self, buyer_name: str, buyer_email: str = None, sale_price: float = None) -> bool:
        """Mark packet as sold and ready for configuration"""
        if not self.can_transition_to(PacketStates.CONFIG_PENDING):
            return False
        
        self.buyer_name = buyer_name
        self.buyer_email = buyer_email
        self.sale_price = sale_price or self.price
        self.sale_date = datetime.now(timezone.utc)
        self.config_state = 'pending'
        
        return self.transition_to(PacketStates.CONFIG_PENDING)
    
    def configure_redirect(self, redirect_url: str) -> bool:
        """Configure packet redirect URL"""
        if self.state != PacketStates.CONFIG_PENDING:
            logger.warning(f"Cannot configure redirect for packet {self.id} in state {self.state}")
            return False
        
        self.redirect_url = redirect_url
        self.config_state = 'done'
        return self.transition_to(PacketStates.CONFIG_DONE)
    
    def get_sale_price(self) -> float:
        """Get the simple sale price for this packet"""
        return self.price or 0.0
    
    def calculate_price(self, price_per_qr: float = 33.0) -> float:
        """Calculate price based on QR count and price per QR (default ₹33 per QR)"""
        if self.price > 0:
            return self.price
        return self.qr_count * price_per_qr
    
    def is_ready_for_sale(self) -> bool:
        """Check if packet is ready to be sold"""
        return self.state == PacketStates.SETUP_DONE
    
    def is_sold(self) -> bool:
        """Check if packet has been sold"""
        return self.state in [PacketStates.CONFIG_PENDING, PacketStates.CONFIG_DONE]
    
    def is_configured(self) -> bool:
        """Check if packet is fully configured"""
        return self.state == PacketStates.CONFIG_DONE and self.redirect_url is not None
    
    def save(self) -> bool:
        """Save packet to Firestore"""
        try:
            db = firestore.client()
            packet_ref = db.collection('packets').document(self.id)
            
            data = self.to_dict()
            packet_ref.set(data)
            
            logger.info(f"Packet {self.id} saved to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving packet {self.id}: {e}")
            return False
    
    def update(self, **kwargs) -> bool:
        """Update packet fields and save to database"""
        try:
            # Update fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            self.updated_at = datetime.now(timezone.utc)
            
            # Save to database
            return self.save()
            
        except Exception as e:
            logger.error(f"Error updating packet {self.id}: {e}")
            return False
    
    @classmethod
    def get_by_id(cls, packet_id: str) -> Optional['Packet']:
        """Get packet by ID from Firestore (excluding deleted ones)"""
        try:
            db = firestore.client()
            doc_ref = db.collection('packets').document(packet_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            data['id'] = doc.id  # Ensure ID is set
            
            # Skip deleted packets
            if data.get('deleted', False):
                return None
            
            return cls.from_dict(data)
            
        except Exception as e:
            logger.error(f"Error retrieving packet {packet_id}: {e}")
            return None
    
    @classmethod
    def get_by_user(cls, user_id: str, limit: int = None) -> List['Packet']:
        """Get all packets for a user (excluding deleted ones)"""
        try:
            db = firestore.client()
            # Use simple query first, then filter in Python to avoid composite index
            query = db.collection('packets').where('user_id', '==', user_id)
            
            if limit:
                query = query.limit(limit * 2)  # Get more to account for filtering
            
            docs = query.stream()
            
            packets = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id  # Ensure ID is set
                
                # Skip deleted packets
                if data.get('deleted', False):
                    continue
                    
                packets.append(cls.from_dict(data))
                
                # Apply limit after filtering
                if limit and len(packets) >= limit:
                    break
            
            return packets
            
        except Exception as e:
            logger.error(f"Error retrieving packets for user {user_id}: {e}")
            return []
    
    @classmethod
    def count_by_user(cls, user_id: str, state: str = None) -> int:
        """Count packets for a user, optionally filtered by state (excluding deleted)"""
        try:
            db = firestore.client()
            query = db.collection('packets').where('user_id', '==', user_id)
            
            docs = query.stream()
            count = 0
            
            for doc in docs:
                data = doc.to_dict()
                
                # Skip deleted packets
                if data.get('deleted', False):
                    continue
                
                # Filter by state if specified
                if state and data.get('state') != state:
                    continue
                    
                count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting packets for user {user_id}: {e}")
            return 0
    
    @classmethod
    def get_by_id_and_user(cls, packet_id: str, user_id: str) -> Optional['Packet']:
        """Get packet by ID and verify ownership"""
        packet = cls.get_by_id(packet_id)
        if packet and packet.user_id == user_id:
            return packet
        return None
    
    @classmethod
    def get_by_master_id(cls, master_id: str) -> Optional['Packet']:
        """Get packet by master ID for updates"""
        try:
            db = firestore.client()
            query = db.collection('packets').where('master_id', '==', master_id)
            docs = list(query.stream())
            
            if not docs:
                return None
            
            doc = docs[0]  # Should be unique
            data = doc.to_dict()
            data['id'] = doc.id
            
            # Skip deleted packets
            if data.get('deleted', False):
                return None
            
            return cls.from_dict(data)
            
        except Exception as e:
            logger.error(f"Error retrieving packet by master_id {master_id}: {e}")
            return None
    
    @classmethod
    def create(cls, user_id: str, qr_count: int = 25, price: float = None) -> Optional['Packet']:
        """Create new packet"""
        try:
            packet = cls(
                user_id=user_id,
                qr_count=qr_count,
                price=price or 0.0  # Simple price field, defaults to 0
            )
            
            if packet.save():
                logger.info(f"Created new packet {packet.id} for user {user_id}")
                return packet
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating packet for user {user_id}: {e}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary for Firestore"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'qr_count': self.qr_count,
            'state': self.state,
            'config_state': self.config_state,
            'price': self.price,
            'base_url': self.base_url,
            'qr_image_url': self.qr_image_url,
            'redirect_url': self.redirect_url,
            'buyer_name': self.buyer_name,
            'buyer_email': self.buyer_email,
            'sale_price': self.sale_price,
            'sale_date': self.sale_date.isoformat() if self.sale_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted': self.deleted,
            'master_id': self.master_id,
            'master_qr_url': self.master_qr_url,
            'packet_password': self.packet_password
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Packet':
        """Create packet from dictionary"""
        # Parse datetime fields
        created_at = None
        if data.get('created_at'):
            try:
                if isinstance(data['created_at'], str):
                    created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                else:
                    # Handle Firestore timestamp
                    created_at = data['created_at']
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing created_at: {e}")
                created_at = datetime.now(timezone.utc)
        
        updated_at = None
        if data.get('updated_at'):
            try:
                if isinstance(data['updated_at'], str):
                    updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
                else:
                    # Handle Firestore timestamp
                    updated_at = data['updated_at']
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing updated_at: {e}")
                updated_at = datetime.now(timezone.utc)
        
        sale_date = None
        if data.get('sale_date'):
            try:
                if isinstance(data['sale_date'], str):
                    sale_date = datetime.fromisoformat(data['sale_date'].replace('Z', '+00:00'))
                else:
                    # Handle Firestore timestamp
                    sale_date = data['sale_date']
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing sale_date: {e}")
        
        return cls(
            packet_id=data.get('id'),
            user_id=data.get('user_id'),
            qr_count=int(data.get('qr_count', 25)) if data.get('qr_count') is not None else 25,
            state=data.get('state', PacketStates.SETUP_DONE),
            config_state=data.get('config_state', 'pending'),
            price=float(data.get('price', 0.0)) if data.get('price') is not None else 0.0,
            base_url=data.get('base_url'),
            qr_image_url=data.get('qr_image_url'),
            redirect_url=data.get('redirect_url'),
            buyer_name=data.get('buyer_name'),
            buyer_email=data.get('buyer_email'),
            sale_price=float(data.get('sale_price')) if data.get('sale_price') is not None else None,
            sale_date=sale_date,
            created_at=created_at,
            updated_at=updated_at,
            deleted=bool(data.get('deleted', False)),
            master_id=data.get('master_id'),
            master_qr_url=data.get('master_qr_url'),
            packet_password=data.get('packet_password')
        )
    
    def delete(self) -> bool:
        """Soft delete the packet (mark as deleted)"""
        try:
            self.deleted = True
            self.updated_at = datetime.now(timezone.utc)
            
            db = firestore.client()
            packet_ref = db.collection('packets').document(self.id)
            packet_ref.update({
                'deleted': True,
                'deleted_at': datetime.now(timezone.utc),
                'updated_at': self.updated_at
            })
            
            logger.info(f"Soft deleted packet {self.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting packet {self.id}: {e}")
            return False
    
    @classmethod
    def delete_by_id(cls, packet_id: str) -> bool:
        """Soft delete packet by ID"""
        try:
            db = firestore.client()
            packet_ref = db.collection('packets').document(packet_id)
            packet_ref.update({
                'deleted': True,
                'deleted_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            })
            logger.info(f"Soft deleted packet {packet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting packet {packet_id}: {e}")
            return False