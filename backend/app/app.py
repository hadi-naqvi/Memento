# app.py

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import base64
import json
import io
from datetime import datetime

# Import the Google RAG system
from google_rag_system import MementoRAGSystem

# Initialize the Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize RAG system
rag_system = MementoRAGSystem(project_id=os.environ.get("GCP_PROJECT_ID"))

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint for patient interaction with the AI assistant"""
    data = request.json
    
    # Validate request
    if not data or 'patientId' not in data or ('message' not in data and 'audio' not in data):
        return jsonify({'error': 'Invalid request. Must include patientId and either message or audio.'}), 400
    
    patient_id = data['patientId']
    
    try:
        # Handle text message
        if 'message' in data:
            message = data['message']
            result = rag_system.process_text_message(patient_id, message)
            
        # Handle audio message
        elif 'audio' in data:
            audio_base64 = data['audio']
            audio_content = base64.b64decode(audio_base64)
            result = rag_system.process_audio_message(patient_id, audio_content)
        
        # Check for errors
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
            
        # Add timestamp to result
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/speech/recognize', methods=['POST'])
def recognize_speech():
    """Convert speech to text"""
    if 'audio' not in request.json:
        return jsonify({'error': 'No audio data provided'}), 400
        
    try:
        audio_base64 = request.json['audio']
        audio_content = base64.b64decode(audio_base64)
        
        # Convert speech to text
        transcript = rag_system.speech_to_text(audio_content)
        
        return jsonify({
            'transcript': transcript,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/speech/synthesize', methods=['POST'])
def synthesize_speech():
    """Convert text to speech"""
    if 'text' not in request.json:
        return jsonify({'error': 'No text provided'}), 400
        
    try:
        text = request.json['text']
        
        # Convert text to speech
        audio_content = rag_system.text_to_speech(text)
        
        # Return as base64
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        return jsonify({
            'audioContent': audio_base64,
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio/stream', methods=['GET'])
def stream_audio():
    """Stream audio file for direct browser playback"""
    audio_base64 = request.args.get('audio')
    
    if not audio_base64:
        return "No audio data provided", 400
        
    try:
        # Decode the base64 audio
        audio_content = base64.b64decode(audio_base64)
        
        # Create a file-like object
        audio_io = io.BytesIO(audio_content)
        
        # Return the audio file
        return send_file(
            audio_io,
            mimetype='audio/mp3',
            as_attachment=False
        )
    except Exception as e:
        return str(e), 500

@app.route('/api/memories', methods=['GET'])
def get_memories():
    """Retrieve memories for a patient based on a query"""
    patient_id = request.args.get('patientId')
    query = request.args.get('query')
    limit = request.args.get('limit', default=5, type=int)
    
    if not patient_id or not query:
        return jsonify({'error': 'Missing patientId or query parameter'}), 400
    
    try:
        memories = rag_system.retrieve_memories(patient_id, query, limit)
        
        # Format for API response
        formatted_memories = []
        for memory in memories:
            formatted_memories.append({
                'summary': memory.get('summary', ''),
                'metadata': memory.get('metadata', {}),
                'similarity': memory.get('similarity', 0.0),
                'timestamp': memory.get('timestamp')
            })
        
        return jsonify({'memories': formatted_memories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Basic login endpoint for testing"""
    data = request.json
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Invalid request. Must include username and password.'}), 400
    
    username = data['username']
    password = data['password']
    
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        # Find user by username
        users = db.collection('users').where('username', '==', username).stream()
        user_list = list(users)
        
        if not user_list:
            return jsonify({'error': 'User not found'}), 404
        
        user_doc = user_list[0]
        user_data = user_doc.to_dict()
        
        # In a real app, you would properly check hashed passwords
        # This is just for demonstration
        if user_data.get('password') != password:
            return jsonify({'error': 'Invalid password'}), 401
        
        # Create mock token
        token = f"demo-token-{user_doc.id}"
        
        return jsonify({
            'userId': user_doc.id,
            'displayName': user_data.get('displayName'),
            'userType': user_data.get('type'),
            'token': token
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# Main entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Starting Memento API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)