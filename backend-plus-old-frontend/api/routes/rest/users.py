from flask import Blueprint, jsonify

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
def get_users():
    """Get all users."""
    return jsonify({"message": "Get users endpoint"}), 200

@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user."""
    return jsonify({"message": f"Get user {user_id} endpoint"}), 200
