from flask import Blueprint, request, jsonify
from firebase_admin import auth
from datetime import datetime, timedelta
import jwt
import json
from functools import wraps
import requests
import os
from dotenv import load_dotenv

from ..db.firebase import db

# Load environment variables
load_dotenv()

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# JWT Configuration from environment
SECRET_KEY = os.getenv("SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# JWT access token creation
def create_access_token(data, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# JWT refresh token creation
def create_refresh_token(data, expires_delta=None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Token verification decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else None
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Verify it's an access token
            if payload.get("type") != "access":
                return jsonify({'message': 'Invalid token type'}), 401
                
            user_id = payload.get('sub')
            if not user_id:
                return jsonify({'message': 'Invalid token'}), 401
            
            # Get user from Firebase
            current_user = auth.get_user(user_id)
        except jwt.PyJWTError:
            return jsonify({'message': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'message': f'Error: {str(e)}'}), 500
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        
        # Create user in Firebase Authentication
        user_record = auth.create_user(
            email=data.get('email'),
            password=data.get('password'),
            display_name=data.get('display_name')
        )
        
        # Store additional user data in Firestore
        user_ref = db.collection('users').document(user_record.uid)
        user_ref.set({
            'username': data.get('username'),
            'email': data.get('email'),
            'displayName': data.get('display_name'),
            'createdAt': datetime.now(),
            'birthDate': data.get('birth_date'),
            'diagnosisType': data.get('diagnosis_type'),
            'profileImageUrl': "",
            'medicationAdherence': 0,
            'memoryScore': 0,
            'dailyQuestionsCompleted': 0,
            'dailyQuestionsTotal': 6,
            'reminders': []
        })
        
        return jsonify({
            'uid': user_record.uid,
            'username': data.get('username'),
            'email': data.get('email'),
            'display_name': data.get('display_name'),
            'message': 'User created successfully'
        }), 201
    
    except auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already registered'}), 400
    except Exception as e:
        return jsonify({'error': f'Error creating user: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        print(f"Login attempt for email: {email}")
        
        if not email or not password:
            print("Missing email or password")
            return jsonify({'error': 'Email and password required'}), 400
        
        try:
            # Authenticate with Firebase Auth REST API
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
            auth_data = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            print(f"Sending request to Firebase Auth API")
            response = requests.post(auth_url, json=auth_data)
            print(f"Firebase Auth response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Firebase Auth error: {response.text}")
                return jsonify({'error': 'Invalid credentials'}), 401
            
            # Authentication successful
            firebase_response = response.json()
            firebase_uid = firebase_response['localId']
            id_token = firebase_response['idToken']
            
            print(f"Successfully authenticated user with UID: {firebase_uid}")
            
            # Look up user in Firestore by email
            users_ref = db.collection('users')
            query = users_ref.where('email', '==', email).limit(1)
            user_docs = query.get()
            
            firestore_user_id = None
            
            if len(user_docs) > 0:
                # Found existing user data in Firestore
                user_doc = user_docs[0]
                user_data = user_doc.to_dict()
                firestore_user_id = user_doc.id
                
                print(f"Found existing user data in Firestore with ID: {firestore_user_id}")
                
                # If the document ID is different from Firebase UID, create a link
                if firestore_user_id != firebase_uid:
                    # Update the existing document with a link to Firebase UID
                    user_doc.reference.update({'firebaseUid': firebase_uid})
                    print(f"Updated Firestore document with Firebase UID reference")
            else:
                # No existing user found in Firestore, create new document using Firebase UID
                print(f"No existing user found in Firestore, creating new document")
                user_ref = db.collection('users').document(firebase_uid)
                user_ref.set({
                    'email': email,
                    'displayName': email.split('@')[0],
                    'createdAt': datetime.now(),
                    'medicationAdherence': 0,
                    'memoryScore': 0,
                    'dailyQuestionsCompleted': 0,
                    'dailyQuestionsTotal': 6,
                    'reminders': [],
                    'diagnosisType': ''
                })
                firestore_user_id = firebase_uid
            
            # Ensure firestore_user_id is not None
            if not firestore_user_id:
                firestore_user_id = firebase_uid
                
            # Create access token for our API
            access_token = create_access_token(
                data={
                    "sub": firebase_uid, 
                    "email": email,
                    "firestore_id": str(firestore_user_id)  # Ensure it's a string
                },
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            # Create refresh token
            refresh_token = create_refresh_token(
                data={
                    "sub": firebase_uid,
                    "firestore_id": str(firestore_user_id)  # Ensure it's a string
                },
                expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            )
            
            print(f"Generated JWT tokens for user: {firebase_uid}")
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'firebase_token': id_token,
                'token_type': 'bearer',
                'user_id': firestore_user_id,  # Return the Firestore document ID for client use
                'firebase_uid': firebase_uid,  # Also return Firebase UID for reference
                'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
            }), 200
        
        except auth.UserNotFoundError:
            print(f"User not found: {email}")
            return jsonify({'error': 'Invalid credentials'}), 401
        except requests.exceptions.RequestException as e:
            print(f"Request error to Firebase Auth: {str(e)}")
            return jsonify({'error': 'Authentication service unavailable'}), 503
        except Exception as e:
            print(f"Error in Firebase Auth: {str(e)}")
            import traceback
            print(traceback.format_exc())  # Print the full traceback for debugging
            return jsonify({'error': f'Login error: {str(e)}'}), 500
        
    except Exception as e:
        print(f"General login error: {str(e)}")
        import traceback
        print(traceback.format_exc())  # Print the full traceback for debugging
        return jsonify({'error': f'Login error: {str(e)}'}), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400
        
        # Verify refresh token
        try:
            payload = jwt.decode(refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if it's a refresh token
            if payload.get("type") != "refresh":
                return jsonify({'error': 'Invalid token type'}), 401
                
            user_id = payload.get("sub")
            
            # Get user from Firebase
            user = auth.get_user(user_id)
            
            # Create new Firebase token
            firebase_token = auth.create_custom_token(user.uid)
            
            # Create new access token
            access_token = create_access_token(
                data={"sub": user.uid, "email": user.email},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            
            # Optionally create new refresh token for rotation
            new_refresh_token = create_refresh_token(
                data={"sub": user.uid},
                expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
            )
            
            return jsonify({
                'access_token': access_token,
                'refresh_token': new_refresh_token,
                'firebase_token': firebase_token.decode("utf-8") if isinstance(firebase_token, bytes) else firebase_token,
                'token_type': 'bearer',
                'expires_in': ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
            }), 200
            
        except jwt.PyJWTError as e:
            return jsonify({'error': f'Invalid refresh token: {str(e)}'}), 401
    
    except Exception as e:
        return jsonify({'error': f'Token refresh error: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    # In a stateful authentication system, we would invalidate the token here
    # Since JWT is stateless, the client should remove the tokens
    
    # For additional security, you could implement a token blacklist/revocation system:
    # 1. Store revoked tokens in a database or Redis
    # 2. Check if tokens are revoked in the token_required decorator
    
    return jsonify({'message': 'Successfully logged out'}), 200