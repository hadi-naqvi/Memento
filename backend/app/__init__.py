from flask import Flask, jsonify, Response, request
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import os
from dotenv import load_dotenv

from .routes.auth import auth_bp
from app.routes.companion import chatbot_bp
from app.routes.reminders import reminder_bp
from app.routes.quizzes import quiz_bp

# Import the database client
from .db.firebase import db
from .db.init_schema import initialize_schema

# Load environment variables
load_dotenv()

jwt = JWTManager()


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)

    # Updated CORS configuration to explicitly allow content-type header
    # CORS(app,
    #      resources={
    #          r"/*": {
    #              "origins": "*",
    #              "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    #              "allow_headers": ["Content-Type", "Authorization", "Accept"]
    #          }
    #      })

    # CORS(app, origins=["http://localhost:3000"], supports_credentials=True, allow_headers=["Content-Type", "Authorization"])

    CORS(app,
     resources={
         r"/*": {
             "origins": ["http://localhost:3000"],  # Keep security, allow only frontend
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Keep all methods
             "allow_headers": ["Content-Type", "Authorization", "Accept"],  # Keep all headers
             "supports_credentials": True  # Keep auth support
         }
     })

    
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    app.config['JWT_REFRESH_SECRET_KEY'] = os.getenv('JWT_REFRESH_SECRET_KEY')
    app.config['JWT_BLACKLIST_ENABLED'] = True
    app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(reminder_bp)
    app.register_blueprint(quiz_bp)

    # Set up database connection
    app.config['FIREBASE_DB'] = db

    # Initialize database schema
    try:
        print("Initializing database schema...")
        initialize_schema()
        print("Database schema initialized successfully!")
    except Exception as e:
        print(f"Error initializing database schema: {e}")
        import traceback
        print(traceback.format_exc())

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    # Handle OPTIONS requests for all routes
    @app.route('/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        return '', 200


    # Import routes and register blueprints
    # Uncomment when routes are ready
    # from .routes import accounts
    # app.register_blueprint(accounts)

    @jwt.unauthorized_loader
    def unauthorized_response(callback: callable) -> Response:
        """
        Handle unauthorized requests.

        Args:
            callback: The callback function.
        
        Returns:
            Flask.Response: JSON response with error message and 401 status code.
        """
        return jsonify({'error': 'You must be logged in.'}), 401

    @jwt.invalid_token_loader
    def invalid_token_response(callback: callable) -> Response:
        """
        Handle invalid tokens.

        Args:
            callback: The callback function.

        Returns:
            Flask.Response: JSON response with error message and 422 status code.
        """
        return jsonify(
            {'error':
             'The provided token is invalid. Please log in again.'}), 422

    @jwt.expired_token_loader
    def expired_token_response(callback: callable) -> Response:
        """
        Handle expired tokens.

        Args:
            callback: The callback function.
        
        Returns:
            Flask.Response: JSON response with error message and 401 status code.
        """
        return jsonify({
            'error':
            'The token has expired. Please log in again to obtain a new token.'
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_response(callback: callable) -> Response:
        """
        Handle revoked tokens.

        Args:
            callback: The callback function.
        
        Returns:
            Flask.Response: JSON response with error message and 401 status code.
        """
        return jsonify({
            'error':
            'The token has been revoked. Please log in again to obtain a new token.'
        }), 401

    @app.errorhandler(404)
    def not_found(error: Exception) -> Response:
        """
        Handle 404 Not Found errors.

        Args:
            error: The error object.

        Returns:
            Flask.Response: JSON response with error message and 404 status code.
        """
        return jsonify({"error": "Route not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error: Exception) -> Response:
        """
        Handle 405 Method Not Allowed errors.

        Args:
            error: The error object.

        Returns:
            Flask.Response: JSON response with error message and 405 status code.
        """
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(error: Exception) -> Response:
        """
        Handle 500 Internal Server Error errors.

        Args:
            error: The error object.

        Returns:
            Flask.Response: JSON response with error message and 500 status code.
        """
        return jsonify({"error": "Internal server error"}), 500

    @app.route('/<path:path>',
               methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    def catch_all(path: str) -> Response:
        """
        Catch all undefined routes and methods.

        Args:
            path (str): The requested path.

        Returns:
            Flask.Response: JSON response with error message and 404 status code.
        """
        if request.method == 'OPTIONS':
            response = jsonify({})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers',
                                 'Content-Type,Authorization,Accept')
            response.headers.add('Access-Control-Allow-Methods',
                                 'GET,POST,PUT,DELETE,OPTIONS')
            return response
        return jsonify(
            {"error":
             "This endpoint does not exist or method is not allowed"}), 404

    return app
