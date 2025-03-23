from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import base64
import uuid
from firebase_admin import firestore
from functools import wraps
import json

# Import the MementoRAGSystem
from app.google_rag_system import MementoRAGSystem

# Create Blueprint
chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/routes/companion')

# Initialize RAG system
rag_system = None


def get_rag_system():
    """Lazy initialization of the RAG system"""
    global rag_system
    if rag_system is None:
        rag_system = MementoRAGSystem(db=current_app.db)
    return rag_system


# Authentication middleware
def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Get token from header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Verify token (implementation depends on your auth system)
            # This is a placeholder - replace with your actual token verification
            user_id = current_app.auth.verify_id_token(token)['uid']
            request.user_id = user_id
        except Exception as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401

        return f(*args, **kwargs)

    return decorated


@chatbot_bp.route('/message', methods=['POST'])
@token_required
def send_message():
    """
    Send a text message to the AI companion
    
    Request body:
    - patient_id: string (required) - ID of the patient
    - message: string (required) - Text message from the patient
    """
    data = request.json

    # Validate input
    if not data or 'message' not in data or 'patient_id' not in data:
        return jsonify(
            {'error': 'Missing required fields: patient_id and message'}), 400

    patient_id = data.get('patient_id')
    message = data.get('message')

    # Process message
    try:
        rag = get_rag_system()
        result = rag.process_text_message(patient_id, message)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error processing message: {str(e)}")
        return jsonify({'error': f'Failed to process message: {str(e)}'}), 500


@chatbot_bp.route('/audio-message', methods=['POST'])
@token_required
def send_audio_message():
    """
    Send an audio message to the AI companion
    
    Request body:
    - patient_id: string (required) - ID of the patient
    - audio: file (required) - Audio file containing the patient's message
    """
    # Check if patient_id is provided
    if 'patient_id' not in request.form:
        return jsonify({'error': 'Missing patient_id field'}), 400

    # Check if audio file is provided
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400

    patient_id = request.form['patient_id']
    audio_file = request.files['audio']

    # Process audio message
    try:
        rag = get_rag_system()
        audio_content = audio_file.read()
        result = rag.process_audio_message(patient_id, audio_content)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error processing audio message: {str(e)}")
        return jsonify({'error':
                        f'Failed to process audio message: {str(e)}'}), 500


@chatbot_bp.route('/history/<patient_id>', methods=['GET'])
@token_required
def get_history(patient_id):
    """
    Get conversation history for a patient
    
    URL Parameters:
    - patient_id: string (required) - ID of the patient
    
    Query Parameters:
    - limit: integer (optional) - Number of messages to retrieve (default: 50)
    - before: string (optional) - Timestamp to retrieve messages before
    """
    # Get query parameters
    try:
        limit = int(request.args.get('limit', 50))
        before_str = request.args.get('before')

        # Parse 'before' timestamp if provided
        before = None
        if before_str:
            before = datetime.fromisoformat(before_str)

    except ValueError as e:
        return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400

    # Retrieve conversation history
    try:
        # Get reference to the conversations collection
        conv_ref = current_app.db.collection("conversations").document(
            patient_id)
        conv_doc = conv_ref.get()

        if not conv_doc.exists:
            return jsonify({'messages': []}), 200

        messages = conv_doc.to_dict().get('messages', [])

        # Filter by timestamp if 'before' is provided
        if before:
            messages = [
                msg for msg in messages
                if 'timestamp' in msg and msg['timestamp'] < before
            ]

        # Sort by timestamp (newest first) and limit
        messages.sort(key=lambda x: x.get('timestamp', datetime.min),
                      reverse=True)
        messages = messages[:limit]

        # Convert datetime objects to ISO strings for JSON serialization
        for msg in messages:
            if 'timestamp' in msg and isinstance(msg['timestamp'], datetime):
                msg['timestamp'] = msg['timestamp'].isoformat()

        return jsonify({'messages': messages}), 200

    except Exception as e:
        current_app.logger.error(
            f"Error retrieving conversation history: {str(e)}")
        return jsonify(
            {'error':
             f'Failed to retrieve conversation history: {str(e)}'}), 500


@chatbot_bp.route('/daily-check/<patient_id>', methods=['GET'])
@token_required
def daily_check(patient_id):
    """
    Initiate or retrieve the daily mood and wellness check
    
    URL Parameters:
    - patient_id: string (required) - ID of the patient
    """
    try:
        # Check if today's check has been completed
        today = datetime.now().replace(hour=0,
                                       minute=0,
                                       second=0,
                                       microsecond=0)
        tomorrow = today + timedelta(days=1)

        # Get daily checks collection
        daily_checks_ref = current_app.db.collection("dailyChecks")

        # Query for today's check
        query = daily_checks_ref.where("patientId", "==", patient_id) \
                               .where("timestamp", ">=", today) \
                               .where("timestamp", "<", tomorrow) \
                               .limit(1)

        checks = list(query.stream())

        if checks:
            # Today's check exists
            check_data = checks[0].to_dict()
            check_data['id'] = checks[0].id

            if check_data.get('completed', False):
                # Check is already completed
                return jsonify({
                    'dailyCheck': check_data,
                    'completed': True
                }), 200
            else:
                # Check exists but is not completed
                return jsonify({
                    'dailyCheck':
                    check_data,
                    'completed':
                    False,
                    'initialPrompt':
                    check_data.get('initialPrompt',
                                   "How are you feeling today?")
                }), 200

        # No check exists for today, create one
        rag = get_rag_system()

        # Get patient info for personalization
        patient_doc = current_app.db.collection("users").document(
            patient_id).get()
        if not patient_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        patient_data = patient_doc.to_dict()
        first_name = patient_data.get("displayName", "").split()[0]

        # Create personalized prompt
        initial_prompt = f"Good morning {first_name}! How are you feeling today? This is our daily check-in."

        # Generate audio for the prompt
        audio_response = rag.text_to_speech(initial_prompt)
        audio_base64 = base64.b64encode(audio_response).decode('utf-8')

        # Create new daily check
        new_check = {
            'patientId': patient_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'completed': False,
            'initialPrompt': initial_prompt,
            'audioPrompt': audio_base64,
            'responses': []
        }

        # Save to Firestore
        check_ref = daily_checks_ref.document()
        check_ref.set(new_check)

        # Return the new check
        new_check['id'] = check_ref.id
        return jsonify({
            'dailyCheck': new_check,
            'completed': False,
            'initialPrompt': initial_prompt,
            'audioPrompt': audio_base64
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error initiating daily check: {str(e)}")
        return jsonify({'error':
                        f'Failed to initiate daily check: {str(e)}'}), 500


@chatbot_bp.route('/reminders', methods=['POST'])
@token_required
def create_reminder():
    """
    Create a new reminder based on conversation context
    
    Request body:
    - patient_id: string (required) - ID of the patient
    - title: string (required) - Reminder title
    - description: string (required) - Reminder description
    - timestamp: string (required) - When the reminder should trigger (ISO format)
    - message_id: string (optional) - ID of the message that triggered this reminder
    """
    data = request.json

    # Validate input
    required_fields = ['patient_id', 'title', 'description', 'timestamp']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        patient_id = data['patient_id']

        # Parse timestamp
        reminder_time = datetime.fromisoformat(data['timestamp'])

        # Create reminder object
        reminder = {
            'id': str(uuid.uuid4()),
            'title': data['title'],
            'description': data['description'],
            'timestamp': reminder_time,
            'isCompleted': False,
            'createdAt': firestore.SERVER_TIMESTAMP
        }

        # Add message_id if provided
        if 'message_id' in data:
            reminder['messageId'] = data['message_id']

        # Add imageUrl if provided
        if 'image_url' in data:
            reminder['imageUrl'] = data['image_url']

        # Get user document
        user_ref = current_app.db.collection('users').document(patient_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404

        # Add reminder to user's reminders array
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        reminders.append(reminder)

        # Update user document
        user_ref.update({'reminders': reminders})

        return jsonify({'reminder_id': reminder['id'], 'success': True}), 200

    except ValueError as e:
        return jsonify({'error': f'Invalid timestamp format: {str(e)}'}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating reminder: {str(e)}")
        return jsonify({'error': f'Failed to create reminder: {str(e)}'}), 500


@chatbot_bp.route('/insights/<patient_id>', methods=['GET'])
@token_required
def get_insights(patient_id):
    """
    Generate conversation insights for a patient
    
    URL Parameters:
    - patient_id: string (required) - ID of the patient
    
    Query Parameters:
    - period: string (optional) - Time period for insights (day, week, month)
    """
    # Get query parameters
    period = request.args.get('period', 'week')

    # Validate period
    valid_periods = ['day', 'week', 'month']
    if period not in valid_periods:
        return jsonify({
            'error':
            f'Invalid period. Must be one of: {", ".join(valid_periods)}'
        }), 400

    try:
        # Calculate start date based on period
        today = datetime.now()
        if period == 'day':
            start_date = today.replace(hour=0,
                                       minute=0,
                                       second=0,
                                       microsecond=0)
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday(), weeks=0)
            start_date = start_date.replace(hour=0,
                                            minute=0,
                                            second=0,
                                            microsecond=0)
        else:  # month
            start_date = today.replace(day=1,
                                       hour=0,
                                       minute=0,
                                       second=0,
                                       microsecond=0)

        # Get conversation messages
        conv_ref = current_app.db.collection("conversations").document(
            patient_id)
        conv_doc = conv_ref.get()

        if not conv_doc.exists:
            return jsonify({
                'topTopics': [],
                'sentimentTrend': [],
                'memoryUsage': {
                    'total': 0,
                    'helpful': 0
                },
                'conversationFrequency': {
                    'total': 0,
                    'perDay': 0
                }
            }), 200

        all_messages = conv_doc.to_dict().get('messages', [])

        # Filter messages by date
        period_messages = [
            msg for msg in all_messages
            if 'timestamp' in msg and msg['timestamp'] >= start_date
        ]

        # Calculate insights

        # 1. Top Topics
        topics_count = {}
        for msg in period_messages:
            if msg.get('sender') == 'patient' and 'topics' in msg:
                for topic in msg.get('topics', []):
                    topics_count[topic] = topics_count.get(topic, 0) + 1

        # Sort topics by count
        top_topics = sorted([{
            'topic': topic,
            'count': count
        } for topic, count in topics_count.items()],
                            key=lambda x: x['count'],
                            reverse=True)[:5]  # Get top 5

        # 2. Sentiment Trend
        sentiment_data = []
        for msg in period_messages:
            if msg.get('sender') == 'patient' and 'sentiment' in msg:
                sentiment_data.append({
                    'timestamp':
                    msg.get('timestamp').isoformat() if isinstance(
                        msg.get('timestamp'), datetime) else
                    msg.get('timestamp'),
                    'sentiment':
                    msg.get('sentiment'),
                    'score':
                    msg.get('sentimentScore', 0)
                })

        # 3. Memory Usage
        memory_count = sum(1 for msg in period_messages if 'memories' in msg)
        helpful_memories = sum(1 for msg in period_messages
                               if msg.get('memoriesHelpful', False))

        # 4. Conversation Frequency
        conversation_days = {}
        for msg in period_messages:
            if 'timestamp' in msg and isinstance(msg.get('timestamp'),
                                                 datetime):
                day_key = msg.get('timestamp').strftime('%Y-%m-%d')
                conversation_days[day_key] = conversation_days.get(day_key,
                                                                   0) + 1

        total_days = (today - start_date).days + 1
        daily_average = len(period_messages) / max(total_days, 1)

        # Compile insights
        insights = {
            'topTopics': top_topics,
            'sentimentTrend': sentiment_data,
            'memoryUsage': {
                'total':
                memory_count,
                'helpful':
                helpful_memories,
                'helpfulPercentage': (helpful_memories / memory_count *
                                      100) if memory_count > 0 else 0
            },
            'conversationFrequency': {
                'total': len(period_messages),
                'perDay': daily_average,
                'activeDays': len(conversation_days),
                'totalDays': total_days
            }
        }

        return jsonify(insights), 200

    except Exception as e:
        current_app.logger.error(f"Error generating insights: {str(e)}")
        return jsonify({'error':
                        f'Failed to generate insights: {str(e)}'}), 500
