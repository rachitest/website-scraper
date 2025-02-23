from flask import Blueprint
from .auth import auth_bp
from .users import users_bp
from .posts import posts_bp

rest_bp = Blueprint('rest', __name__)

def register_rest_routes(app):
    """Register REST API routes."""
    # Register individual blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(posts_bp, url_prefix='/api/v1/posts')