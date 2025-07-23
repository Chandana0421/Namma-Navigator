# firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
from datetime import datetime

class FirebaseConfig:
    def __init__(self):
        self.db = None
        self.bucket = None
        
    def initialize(self):
        """Initialize Firebase with your service account"""
        if not firebase_admin._apps:
            # Use service account key from config directory
            cred = credentials.Certificate('config/firebase-service-account.json')
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'namma-navigator.appspot.com'
            })
            
        self.db = firestore.client()
        self.bucket = storage.bucket()
        
        print("✅ Firebase initialized successfully")
        return self.db, self.bucket
    
    def get_database(self):
        """Get Firestore database client"""
        if not self.db:
            self.initialize()
        return self.db
    
    def get_storage(self):
        """Get Firebase Storage bucket"""
        if not self.bucket:
            self.initialize()
        return self.bucket

# Global instance for easy importing
firebase_config = FirebaseConfig()

# Convenience functions
def initialize_firebase():
    """Initialize and return Firebase services"""
    return firebase_config.initialize()

def get_db():
    """Get Firestore database"""
    return firebase_config.get_database()

def get_storage():
    """Get Firebase Storage"""
    return firebase_config.get_storage()
