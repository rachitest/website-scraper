from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from dotenv import load_dotenv
import os
import logging
from api.utils.logger import setup_logger
from urllib.parse import urlparse

# Load environment variables, ignoring comments
load_dotenv(override=True)

# Initialize logger
logger = setup_logger(__name__)

# Get port from environment variables with fallback logic
def get_api_port():
    api_port = os.environ.get("API_PORT")
    if api_port:
        try:
            return int(api_port)
        except ValueError:
            logger.warning(f"Invalid API_PORT value: {api_port}. Using default port 5000.")
            return 5000

    api_url = os.environ.get("API_URL")
    if api_url:
        try:
            parsed_port = urlparse(api_url).port
            if parsed_port:
                return parsed_port
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse port from API_URL: {api_url}. Using default port 5000.")

    logger.info("No API_PORT or valid API_URL port found. Using default port 5000.")
    return 5000

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    return app

def create_app():
    """Create and configure the Flask application."""
    app = init_app()  # Get the base app

    # Get the API and APP URLs from environment with logging
    api_url = os.environ.get("API_URL")
    if not api_url:
        api_url = "http://localhost:5000"
        logger.info(f"API_URL not set. Using default: {api_url}")
    
    app_url = os.environ.get("APP_URL")
    if not app_url:
        app_url = "http://localhost:3000"
        logger.info(f"APP_URL not set. Using default: {app_url}")

    # Enable CORS for development
    CORS(app, resources={
        r"/api/*": {
            "origins": [app_url],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Set secret key with fallback
    secret_key = os.environ.get("SESSION_SECRET")
    if not secret_key:
        secret_key = 'dev_secret_key'
        logger.warning("SESSION_SECRET not set. Using insecure default for development.")
    app.secret_key = secret_key

    # Configure the database with validation
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        database_url = "sqlite:///dev.db"
        logger.info(f"Using default SQLite database: {database_url}")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Initialize extensions
    db.init_app(app)

    with app.app_context():
        # Import routes
        from api.routes.rest import register_rest_routes
        from api.routes.graphql import register_graphql_routes
        from api.routes.trpc import register_trpc_routes

        # Register routes
        register_rest_routes(app)
        register_graphql_routes(app)
        register_trpc_routes(app)

        # Create database tables
        db.create_all()

        @app.route("/")
        def index():
            """Root endpoint that lists available API endpoints."""
            return jsonify({
                "message": "Welcome to mini-api-v2",
                "version": "0.1.0",
                "endpoints": {
                    "rest": {
                        "base": "/api/v1",
                        "health": "/api/health",
                        "auth": "/api/v1/auth/*",
                        "users": "/api/v1/users/*",
                        "posts": "/api/v1/posts/*"
                    },
                    "graphql": "/graphql",
                    "trpc": "/trpc/*"
                }
            })

        @app.route("/api/health")
        def health_check():
            """Health check endpoint."""
            try:
                db.session.execute(text("SELECT 1"))
                return jsonify({
                    "status": "healthy",
                    "database": "connected",
                    "api_url": os.environ.get("API_URL"),
                    "app_url": os.environ.get("APP_URL")
                })
            except Exception as e:
                logger.error(f"Health check failed: {str(e)}")
                return jsonify({"status": "unhealthy", "error": str(e)}), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = get_api_port()
    logger.info(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)