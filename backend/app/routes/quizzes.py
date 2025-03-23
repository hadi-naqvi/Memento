from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from datetime import datetime, timedelta

# Import the MementoQuizSystem
from app.quiz_system import MementoQuizSystem

# Create Blueprint
quiz_bp = Blueprint('quizzes', __name__, url_prefix='/routes/quizzes')

# Initialize Quiz system
quiz_system = None


def get_quiz_system():
    """Lazy initialization of the Quiz system"""
    global quiz_system
    if quiz_system is None:
        quiz_system = MementoQuizSystem(db=current_app.config['FIREBASE_DB'])
    return quiz_system


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


@quiz_bp.route('/generate', methods=['POST'])
@token_required
def generate_quiz():
    """
    Generate a new quiz for a patient
    
    Request body:
    - patient_id: string (required) - ID of the patient
    - quiz_type: string (optional) - Type of quiz ('memory', 'conversation', 'mixed', 'general')
    - question_count: int (optional) - Number of questions to generate (default: 5)
    """
    data = request.json

    # Validate input
    if not data or 'patient_id' not in data:
        return jsonify({'error': 'Missing required field: patient_id'}), 400

    # Get parameters
    patient_id = data.get('patient_id')
    quiz_type = data.get('quiz_type', 'mixed')
    question_count = data.get('question_count', 5)

    # Validate quiz_type
    valid_types = ['memory', 'conversation', 'mixed', 'general']
    if quiz_type not in valid_types:
        return jsonify({
            'error':
            f'Invalid quiz_type. Must be one of: {", ".join(valid_types)}'
        }), 400

    # Validate question_count
    try:
        question_count = int(question_count)
        if question_count < 1 or question_count > 10:
            return jsonify(
                {'error': 'question_count must be between 1 and 10'}), 400
    except ValueError:
        return jsonify({'error': 'question_count must be an integer'}), 400

    # Generate quiz
    try:
        quiz_system = get_quiz_system()
        result = quiz_system.generate_quiz(patient_id=patient_id,
                                           quiz_type=quiz_type,
                                           question_count=question_count)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error generating quiz: {str(e)}")
        return jsonify({'error': f'Failed to generate quiz: {str(e)}'}), 500


@quiz_bp.route('/answer', methods=['POST'])
@token_required
def submit_answer():
    """
    Submit an answer to a quiz question
    
    Request body:
    - quiz_id: string (required) - ID of the quiz session
    - question_id: string (required) - ID of the question being answered
    - selected_option: string (required) - The option selected by the patient (A, B, C, or D)
    """
    data = request.json

    # Validate input
    required_fields = ['quiz_id', 'question_id', 'selected_option']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Get parameters
    quiz_id = data.get('quiz_id')
    question_id = data.get('question_id')
    selected_option = data.get('selected_option')

    # Validate selected_option
    valid_options = ['A', 'B', 'C', 'D']
    if selected_option not in valid_options:
        return jsonify({
            'error':
            f'Invalid selected_option. Must be one of: {", ".join(valid_options)}'
        }), 400

    # Record answer
    try:
        quiz_system = get_quiz_system()
        result = quiz_system.record_quiz_answer(
            quiz_id=quiz_id,
            question_id=question_id,
            selected_option=selected_option)

        if 'error' in result:
            return jsonify({'error': result['error']}), 400

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error recording quiz answer: {str(e)}")
        return jsonify({'error': f'Failed to record answer: {str(e)}'}), 500


@quiz_bp.route('/<quiz_id>', methods=['GET'])
@token_required
def get_quiz(quiz_id):
    """
    Get details of a specific quiz session
    
    URL Parameters:
    - quiz_id: string (required) - ID of the quiz session
    """
    try:
        quiz_system = get_quiz_system()
        result = quiz_system.get_quiz_session(quiz_id)

        if 'error' in result:
            return jsonify({'error': result['error']}), 404

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving quiz: {str(e)}")
        return jsonify({'error': f'Failed to retrieve quiz: {str(e)}'}), 500


@quiz_bp.route('/history', methods=['GET'])
@token_required
def get_quiz_history():
    """
    Get quiz history for a patient
    
    Query Parameters:
    - patient_id: string (required) - ID of the patient
    - limit: int (optional) - Maximum number of results to return
    """
    # Get query parameters
    patient_id = request.args.get('patient_id')
    limit = request.args.get('limit', 10, type=int)

    # Validate patient_id
    if not patient_id:
        return jsonify({'error':
                        'Missing required parameter: patient_id'}), 400

    # Validate limit
    if limit < 1:
        return jsonify({'error': 'limit must be a positive integer'}), 400

    # Get history
    try:
        quiz_system = get_quiz_system()
        result = quiz_system.get_patient_quiz_history(patient_id=patient_id,
                                                      limit=limit)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving quiz history: {str(e)}")
        return jsonify({'error':
                        f'Failed to retrieve quiz history: {str(e)}'}), 500


@quiz_bp.route('/categories', methods=['GET'])
def get_quiz_categories():
    """
    Get available quiz categories
    """
    categories = [{
        "id": "memory",
        "name": "Memory Quiz",
        "description": "Questions based on patient's personal memories",
        "icon": "brain"
    }, {
        "id": "conversation",
        "name": "Conversation Quiz",
        "description": "Questions based on recent conversations",
        "icon": "message-circle"
    }, {
        "id": "mixed",
        "name": "Mixed Quiz",
        "description": "Combination of memory and conversation questions",
        "icon": "layers"
    }, {
        "id": "general",
        "name": "General Knowledge",
        "description": "Simple general knowledge questions",
        "icon": "book-open"
    }]

    return jsonify({"categories": categories}), 200


@quiz_bp.route('/stats', methods=['GET'])
@token_required
def get_quiz_stats():
    """
    Get quiz statistics for a patient
    
    Query Parameters:
    - patient_id: string (required) - ID of the patient
    - days: int (optional) - Number of days to include in statistics (default: 30)
    """
    # Get query parameters
    patient_id = request.args.get('patient_id')
    days = request.args.get('days', 30, type=int)

    # Validate patient_id
    if not patient_id:
        return jsonify({'error':
                        'Missing required parameter: patient_id'}), 400

    try:
        # Get Firestore connection
        db = current_app.config['FIREBASE_DB']

        # Calculate time window
        now = datetime.now()
        start_date = now - timedelta(days=days)

        # Query for completed quizzes in the time window
        quiz_query = db.collection("quizSessions") \
            .where("patientId", "==", patient_id) \
            .where("status", "==", "completed") \
            .where("completedAt", ">=", start_date) \
            .stream()

        # Process the quiz data
        quizzes = []
        for doc in quiz_query:
            quiz_data = doc.to_dict()
            quiz_info = {
                "id": quiz_data.get("id"),
                "quizType": quiz_data.get("quizType", "unknown"),
                "score": quiz_data.get("score", 0),
                "completedAt": quiz_data.get("completedAt")
            }

            # Convert datetime to string if needed
            if isinstance(quiz_info["completedAt"], datetime):
                quiz_info["completedAt"] = quiz_info["completedAt"].isoformat()

            quizzes.append(quiz_info)

        # Calculate statistics
        total_quizzes = len(quizzes)
        if total_quizzes == 0:
            return jsonify({
                "totalQuizzes": 0,
                "averageScore": 0,
                "quizzesByType": {},
                "scoresByType": {},
                "recentScores": [],
                "scoreTrend": []
            }), 200

        # Sort quizzes by date
        quizzes.sort(key=lambda q: q["completedAt"])

        # Average score
        avg_score = sum(q["score"] for q in quizzes) / total_quizzes

        # Quizzes by type
        quizzes_by_type = {}
        scores_by_type = {}

        for quiz in quizzes:
            quiz_type = quiz["quizType"]
            if quiz_type not in quizzes_by_type:
                quizzes_by_type[quiz_type] = 0
                scores_by_type[quiz_type] = []

            quizzes_by_type[quiz_type] += 1
            scores_by_type[quiz_type].append(quiz["score"])

        # Calculate average score by type
        avg_scores_by_type = {}
        for quiz_type, scores in scores_by_type.items():
            avg_scores_by_type[quiz_type] = sum(scores) / len(scores)

        # Recent scores (last 10)
        recent_scores = [q["score"] for q in quizzes[-10:]]

        # Score trend data (for charts)
        score_trend = []
        for quiz in quizzes:
            score_trend.append({
                "date": quiz["completedAt"],
                "score": quiz["score"],
                "type": quiz["quizType"]
            })

        return jsonify({
            "totalQuizzes": total_quizzes,
            "averageScore": round(avg_score, 1),
            "quizzesByType": quizzes_by_type,
            "scoresByType": avg_scores_by_type,
            "recentScores": recent_scores,
            "scoreTrend": score_trend
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving quiz statistics: {str(e)}")
        return jsonify(
            {'error': f'Failed to retrieve quiz statistics: {str(e)}'}), 500
