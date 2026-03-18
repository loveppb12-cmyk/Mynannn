from pymongo import MongoClient
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, uri, db_name):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.users = self.db["users"]
        
    def save_user(self, user_id, phone, session_string):
        """Save user data to database"""
        try:
            result = self.users.insert_one({
                "user_id": user_id,
                "phone": phone,
                "session_string": session_string,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "active": False
            })
            return True
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False
    
    def get_user(self, user_id):
        """Get user data by user_id"""
        return self.users.find_one({"user_id": user_id})
    
    def update_user_status(self, user_id, active):
        """Update userbot active status"""
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"active": active}}
        )
    
    def delete_user(self, user_id):
        """Delete user from database"""
        return self.users.delete_one({"user_id": user_id})
    
    def get_all_users(self):
        """Get all users (for admin purposes)"""
        return list(self.users.find())
    
    def close(self):
        """Close database connection"""
        self.client.close()
