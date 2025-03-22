# firebase_init.py
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Keep track of initialization status
_initialized = False
_db = None


def initialize_firebase():
    global _initialized, _db

    if _initialized:
        return _db

    try:
        # Check if Firebase is already initialized
        try:
            app = firebase_admin.get_app()
            print("Firebase already initialized")
        except ValueError:
            # Initialize Firebase
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if not cred_path:
                raise ValueError(
                    "FIREBASE_CREDENTIALS_PATH environment variable not set")

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")

        # Get Firestore client
        _db = firestore.client()
        _initialized = True
        return _db
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        raise


# Initialize Firebase when this module is imported
db = initialize_firebase()
