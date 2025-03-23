from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
import uuid
from firebase_admin import firestore
from functools import wraps

# Create Blueprint
reminder_bp = Blueprint('reminders', __name__, url_prefix='/routes/reminders')

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
            user_id = current_app.jwt.verify_id_token(token)['uid']
            request.user_id = user_id
        except Exception as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
            
        return f(*args, **kwargs)
    
    return decorated

@reminder_bp.route('/', methods=['GET'])
@token_required
def get_reminders():
    """
    Get all reminders for a patient
    
    Query Parameters:
    - patient_id: string (required) - ID of the patient
    - status: string (optional) - Filter by status ('all', 'active', 'completed')
    - from_date: string (optional) - Start date for filtering (ISO format)
    - to_date: string (optional) - End date for filtering (ISO format)
    """
    # Get query parameters
    patient_id = request.args.get('patient_id')
    status = request.args.get('status', 'all')
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')
    
    # Validate patient_id
    if not patient_id:
        return jsonify({'error': 'Missing required parameter: patient_id'}), 400
    
    try:
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Get reminders from user document
        user_data = user_doc.to_dict()
        all_reminders = user_data.get('reminders', [])
        
        # Parse dates if provided
        from_date = None
        to_date = None
        if from_date_str:
            try:
                from_date = datetime.fromisoformat(from_date_str)
            except ValueError:
                return jsonify({'error': 'Invalid from_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
                
        if to_date_str:
            try:
                to_date = datetime.fromisoformat(to_date_str)
            except ValueError:
                return jsonify({'error': 'Invalid to_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Filter reminders
        filtered_reminders = []
        for reminder in all_reminders:
            # Skip if timestamp is missing
            if 'timestamp' not in reminder:
                continue
                
            reminder_time = reminder['timestamp']
            
            # Status filter
            if status != 'all':
                is_completed = reminder.get('isCompleted', False)
                if (status == 'completed' and not is_completed) or (status == 'active' and is_completed):
                    continue
            
            # Date range filter
            if from_date and reminder_time < from_date:
                continue
                
            if to_date and reminder_time > to_date:
                continue
                
            filtered_reminders.append(reminder)
        
        # Convert datetime objects to ISO strings for JSON serialization
        for reminder in filtered_reminders:
            if 'timestamp' in reminder and isinstance(reminder['timestamp'], datetime):
                reminder['timestamp'] = reminder['timestamp'].isoformat()
            if 'createdAt' in reminder and isinstance(reminder['createdAt'], datetime):
                reminder['createdAt'] = reminder['createdAt'].isoformat()
        
        return jsonify({
            'reminders': filtered_reminders,
            'total': len(filtered_reminders)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving reminders: {str(e)}")
        return jsonify({'error': f'Failed to retrieve reminders: {str(e)}'}), 500

@reminder_bp.route('/', methods=['POST'])
@token_required
def create_reminder():
    """
    Create a new reminder
    
    Request body:
    - patient_id: string (required) - ID of the patient
    - title: string (required) - Reminder title
    - description: string (required) - Reminder description
    - timestamp: string (required) - When the reminder should trigger (ISO format)
    - image_url: string (optional) - URL to an image for the reminder
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
        try:
            reminder_time = datetime.fromisoformat(data['timestamp'])
        except ValueError:
            return jsonify({'error': 'Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Create reminder object
        reminder = {
            'id': str(uuid.uuid4()),
            'title': data['title'],
            'description': data['description'],
            'timestamp': reminder_time,
            'isCompleted': False,
            'createdAt': firestore.SERVER_TIMESTAMP
        }
        
        # Add optional fields
        if 'image_url' in data:
            reminder['imageUrl'] = data['image_url']
        
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Add reminder to user's reminders array
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        reminders.append(reminder)
        
        # Update user document
        user_ref.update({'reminders': reminders})
        
        # Return the created reminder (convert timestamps to strings)
        reminder_response = reminder.copy()
        reminder_response['timestamp'] = reminder_time.isoformat()
        
        return jsonify({
            'reminder': reminder_response,
            'message': 'Reminder created successfully'
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating reminder: {str(e)}")
        return jsonify({'error': f'Failed to create reminder: {str(e)}'}), 500

@reminder_bp.route('/<reminder_id>', methods=['GET'])
@token_required
def get_reminder(reminder_id):
    """
    Get a specific reminder
    
    URL Parameters:
    - reminder_id: string (required) - ID of the reminder
    
    Query Parameters:
    - patient_id: string (required) - ID of the patient
    """
    patient_id = request.args.get('patient_id')
    
    if not patient_id:
        return jsonify({'error': 'Missing required parameter: patient_id'}), 400
    
    try:
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Find the specific reminder
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        
        reminder = next((r for r in reminders if r.get('id') == reminder_id), None)
        
        if not reminder:
            return jsonify({'error': 'Reminder not found'}), 404
        
        # Convert datetime objects to ISO strings for JSON serialization
        reminder_response = reminder.copy()
        if 'timestamp' in reminder_response and isinstance(reminder_response['timestamp'], datetime):
            reminder_response['timestamp'] = reminder_response['timestamp'].isoformat()
        if 'createdAt' in reminder_response and isinstance(reminder_response['createdAt'], datetime):
            reminder_response['createdAt'] = reminder_response['createdAt'].isoformat()
        
        return jsonify({'reminder': reminder_response}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving reminder: {str(e)}")
        return jsonify({'error': f'Failed to retrieve reminder: {str(e)}'}), 500

@reminder_bp.route('/<reminder_id>', methods=['PUT'])
@token_required
def update_reminder(reminder_id):
    """
    Update a specific reminder
    
    URL Parameters:
    - reminder_id: string (required) - ID of the reminder
    
    Request body:
    - patient_id: string (required) - ID of the patient
    - title: string (optional) - Updated reminder title
    - description: string (optional) - Updated reminder description
    - timestamp: string (optional) - Updated timestamp (ISO format)
    - is_completed: boolean (optional) - Updated completion status
    - image_url: string (optional) - Updated image URL
    """
    data = request.json
    
    if 'patient_id' not in data:
        return jsonify({'error': 'Missing required field: patient_id'}), 400
    
    patient_id = data['patient_id']
    
    try:
        # Parse timestamp if provided
        reminder_time = None
        if 'timestamp' in data:
            try:
                reminder_time = datetime.fromisoformat(data['timestamp'])
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
        
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Find and update the specific reminder
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        
        reminder_index = next((i for i, r in enumerate(reminders) if r.get('id') == reminder_id), None)
        
        if reminder_index is None:
            return jsonify({'error': 'Reminder not found'}), 404
        
        # Update reminder fields
        reminder = reminders[reminder_index]
        
        if 'title' in data:
            reminder['title'] = data['title']
        if 'description' in data:
            reminder['description'] = data['description']
        if reminder_time:
            reminder['timestamp'] = reminder_time
        if 'is_completed' in data:
            reminder['isCompleted'] = bool(data['is_completed'])
        if 'image_url' in data:
            reminder['imageUrl'] = data['image_url']
        
        # Update the reminder in the list
        reminders[reminder_index] = reminder
        
        # Update user document
        user_ref.update({'reminders': reminders})
        
        # Prepare response
        reminder_response = reminder.copy()
        if 'timestamp' in reminder_response and isinstance(reminder_response['timestamp'], datetime):
            reminder_response['timestamp'] = reminder_response['timestamp'].isoformat()
        if 'createdAt' in reminder_response and isinstance(reminder_response['createdAt'], datetime):
            reminder_response['createdAt'] = reminder_response['createdAt'].isoformat()
        
        return jsonify({
            'reminder': reminder_response,
            'message': 'Reminder updated successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating reminder: {str(e)}")
        return jsonify({'error': f'Failed to update reminder: {str(e)}'}), 500

@reminder_bp.route('/<reminder_id>/complete', methods=['POST'])
@token_required
def complete_reminder(reminder_id):
    """
    Mark a reminder as completed
    
    URL Parameters:
    - reminder_id: string (required) - ID of the reminder
    
    Request body:
    - patient_id: string (required) - ID of the patient
    """
    data = request.json
    
    if 'patient_id' not in data:
        return jsonify({'error': 'Missing required field: patient_id'}), 400
    
    patient_id = data['patient_id']
    
    try:
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Find the specific reminder
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        
        reminder_index = next((i for i, r in enumerate(reminders) if r.get('id') == reminder_id), None)
        
        if reminder_index is None:
            return jsonify({'error': 'Reminder not found'}), 404
        
        # Mark as completed
        reminders[reminder_index]['isCompleted'] = True
        reminders[reminder_index]['completedAt'] = firestore.SERVER_TIMESTAMP
        
        # Update user document
        user_ref.update({'reminders': reminders})
        
        return jsonify({
            'message': 'Reminder marked as completed',
            'reminder_id': reminder_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error completing reminder: {str(e)}")
        return jsonify({'error': f'Failed to complete reminder: {str(e)}'}), 500

@reminder_bp.route('/<reminder_id>', methods=['DELETE'])
@token_required
def delete_reminder(reminder_id):
    """
    Delete a specific reminder
    
    URL Parameters:
    - reminder_id: string (required) - ID of the reminder
    
    Query Parameters:
    - patient_id: string (required) - ID of the patient
    """
    patient_id = request.args.get('patient_id')
    
    if not patient_id:
        return jsonify({'error': 'Missing required parameter: patient_id'}), 400
    
    try:
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Find and remove the specific reminder
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        
        reminder_index = next((i for i, r in enumerate(reminders) if r.get('id') == reminder_id), None)
        
        if reminder_index is None:
            return jsonify({'error': 'Reminder not found'}), 404
        
        # Remove the reminder
        del reminders[reminder_index]
        
        # Update user document
        user_ref.update({'reminders': reminders})
        
        return jsonify({
            'message': 'Reminder deleted successfully',
            'reminder_id': reminder_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting reminder: {str(e)}")
        return jsonify({'error': f'Failed to delete reminder: {str(e)}'}), 500

@reminder_bp.route('/upcoming', methods=['GET'])
@token_required
def get_upcoming_reminders():
    """
    Get upcoming reminders for a patient
    
    Query Parameters:
    - patient_id: string (required) - ID of the patient
    - hours: integer (optional) - Number of hours to look ahead (default: 24)
    - limit: integer (optional) - Maximum number of reminders to return (default: 10)
    """
    patient_id = request.args.get('patient_id')
    hours = request.args.get('hours', 24, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    if not patient_id:
        return jsonify({'error': 'Missing required parameter: patient_id'}), 400
    
    try:
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Calculate time window
        now = datetime.now()
        end_time = now + timedelta(hours=hours)
        
        # Find upcoming reminders
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        
        upcoming_reminders = []
        for reminder in reminders:
            # Skip if timestamp is missing or reminder is completed
            if 'timestamp' not in reminder or reminder.get('isCompleted', False):
                continue
                
            reminder_time = reminder['timestamp']
            
            # Check if reminder is within the time window
            if now <= reminder_time <= end_time:
                upcoming_reminders.append(reminder)
        
        # Sort by timestamp (earliest first)
        upcoming_reminders.sort(key=lambda r: r['timestamp'])
        
        # Limit the number of results
        upcoming_reminders = upcoming_reminders[:limit]
        
        # Convert datetime objects to ISO strings for JSON serialization
        for reminder in upcoming_reminders:
            if 'timestamp' in reminder and isinstance(reminder['timestamp'], datetime):
                reminder['timestamp'] = reminder['timestamp'].isoformat()
            if 'createdAt' in reminder and isinstance(reminder['createdAt'], datetime):
                reminder['createdAt'] = reminder['createdAt'].isoformat()
        
        return jsonify({
            'reminders': upcoming_reminders,
            'total': len(upcoming_reminders)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving upcoming reminders: {str(e)}")
        return jsonify({'error': f'Failed to retrieve upcoming reminders: {str(e)}'}), 500

@reminder_bp.route('/stats', methods=['GET'])
@token_required
def get_reminder_stats():
    """
    Get reminder statistics for a patient
    
    Query Parameters:
    - patient_id: string (required) - ID of the patient
    - days: integer (optional) - Number of days to analyze (default: 30)
    """
    patient_id = request.args.get('patient_id')
    days = request.args.get('days', 30, type=int)
    
    if not patient_id:
        return jsonify({'error': 'Missing required parameter: patient_id'}), 400
    
    try:
        # Get user document
        user_ref = current_app.config['FIREBASE_DB'].collection('users').document(patient_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Calculate time window
        now = datetime.now()
        start_time = now - timedelta(days=days)
        
        # Analyze reminders
        user_data = user_doc.to_dict()
        reminders = user_data.get('reminders', [])
        
        # Initialize statistics
        stats = {
            'total': 0,
            'completed': 0,
            'missed': 0,
            'upcoming': 0,
            'completion_rate': 0,
            'by_category': {},
            'daily_completion': [0] * (days + 1),  # One entry per day
            'completion_trend': []
        }
        
        # Categorize reminders
        category_counts = {}
        daily_reminders = {}
        daily_completed = {}
        
        for reminder in reminders:
            # Skip if timestamp is missing
            if 'timestamp' not in reminder:
                continue
                
            reminder_time = reminder['timestamp']
            is_completed = reminder.get('isCompleted', False)
            
            # Get the reminder type/category (e.g., medication, appointment)
            category = reminder.get('title', 'other').split()[0].lower()
            
            # Count by category
            if category not in category_counts:
                category_counts[category] = {'total': 0, 'completed': 0}
            category_counts[category]['total'] += 1
            if is_completed:
                category_counts[category]['completed'] += 1
            
            # Check if reminder is within the analysis period
            if start_time <= reminder_time <= now:
                stats['total'] += 1
                
                # Count completed vs missed
                if is_completed:
                    stats['completed'] += 1
                else:
                    stats['missed'] += 1
                
                # Track daily completion
                day_index = (now - reminder_time).days
                if 0 <= day_index <= days:
                    # Initialize daily counts if needed
                    day_str = reminder_time.strftime('%Y-%m-%d')
                    if day_str not in daily_reminders:
                        daily_reminders[day_str] = 0
                        daily_completed[day_str] = 0
                    
                    daily_reminders[day_str] += 1
                    if is_completed:
                        daily_completed[day_str] += 1
            
            # Count upcoming reminders
            elif reminder_time > now and not is_completed:
                stats['upcoming'] += 1
        
        # Calculate completion rate
        if stats['total'] > 0:
            stats['completion_rate'] = round((stats['completed'] / stats['total']) * 100, 1)
        
        # Format category statistics
        for category, counts in category_counts.items():
            completion_rate = 0
            if counts['total'] > 0:
                completion_rate = round((counts['completed'] / counts['total']) * 100, 1)
            
            stats['by_category'][category] = {
                'total': counts['total'],
                'completed': counts['completed'],
                'completion_rate': completion_rate
            }
        
        # Format daily completion trend
        for i in range(days + 1):
            day_date = now - timedelta(days=i)
            day_str = day_date.strftime('%Y-%m-%d')
            
            total = daily_reminders.get(day_str, 0)
            completed = daily_completed.get(day_str, 0)
            rate = 0 if total == 0 else round((completed / total) * 100, 1)
            
            stats['completion_trend'].append({
                'date': day_str,
                'total': total,
                'completed': completed,
                'rate': rate
            })
        
        # Sort trend by date (oldest first)
        stats['completion_trend'].reverse()
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving reminder statistics: {str(e)}")
        return jsonify({'error': f'Failed to retrieve reminder statistics: {str(e)}'}), 500

def init_app(app):
    """Initialize the blueprint with the Flask app"""
    app.register_blueprint(reminder_bp)