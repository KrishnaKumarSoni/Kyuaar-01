"""
Activity model for tracking user actions and system events
Provides activity feed for dashboard
"""

import logging
from datetime import datetime, timezone
from firebase_admin import firestore
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ActivityType:
    """Constants for activity types"""
    PACKET_CREATED = 'packet_created'
    PACKET_UPLOADED = 'packet_uploaded'
    PACKET_SOLD = 'packet_sold'
    PACKET_CONFIGURED = 'packet_configured'
    PACKET_DELETED = 'packet_deleted'
    USER_LOGIN = 'user_login'
    USER_REGISTER = 'user_register'
    SETTINGS_UPDATED = 'settings_updated'

class Activity:
    """Activity model for tracking user actions"""
    
    def __init__(self, activity_id: str = None, user_id: str = None, 
                 activity_type: str = None, title: str = None, 
                 description: str = None, metadata: Dict = None,
                 created_at: datetime = None):
        self.id = activity_id
        self.user_id = user_id
        self.activity_type = activity_type
        self.title = title
        self.description = description
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert activity to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'title': self.title,
            'description': self.description,
            'metadata': self.metadata,
            'created_at': self.created_at
        }
    
    @staticmethod
    def log(user_id: str, activity_type: str, title: str, description: str = None, metadata: Dict = None):
        """Log new activity"""
        try:
            db = firestore.client()
            
            activity_data = {
                'user_id': user_id,
                'activity_type': activity_type,
                'title': title,
                'description': description or '',
                'metadata': metadata or {},
                'created_at': datetime.now(timezone.utc)
            }
            
            # Add to Firestore
            doc_ref = db.collection('activities').add(activity_data)
            activity_id = doc_ref[1].id
            
            logger.info(f"Activity logged: {activity_type} for user {user_id}")
            
            return Activity(
                activity_id=activity_id,
                user_id=user_id,
                activity_type=activity_type,
                title=title,
                description=description,
                metadata=metadata,
                created_at=activity_data['created_at']
            )
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
            return None
    
    @staticmethod
    def get_recent_by_user(user_id: str, limit: int = 10) -> List['Activity']:
        """Get recent activities for a user"""
        try:
            db = firestore.client()
            query = (db.collection('activities')
                    .where('user_id', '==', user_id)
                    .order_by('created_at', direction='DESCENDING')
                    .limit(limit))
            
            activities = []
            for doc in query.stream():
                data = doc.to_dict()
                activity = Activity(
                    activity_id=doc.id,
                    user_id=data['user_id'],
                    activity_type=data['activity_type'],
                    title=data['title'],
                    description=data.get('description'),
                    metadata=data.get('metadata', {}),
                    created_at=data['created_at']
                )
                activities.append(activity)
            
            return activities
            
        except Exception as e:
            logger.error(f"Error getting recent activities for user {user_id}: {e}")
            return []
    
    @staticmethod
    def get_statistics_by_user(user_id: str) -> Dict[str, int]:
        """Get activity statistics for a user"""
        try:
            db = firestore.client()
            activities = list(db.collection('activities')
                            .where('user_id', '==', user_id)
                            .stream())
            
            stats = {}
            for doc in activities:
                data = doc.to_dict()
                activity_type = data['activity_type']
                stats[activity_type] = stats.get(activity_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting activity statistics for user {user_id}: {e}")
            return {}