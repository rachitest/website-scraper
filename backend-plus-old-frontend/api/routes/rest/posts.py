from flask import Blueprint, jsonify

posts_bp = Blueprint('posts', __name__)

@posts_bp.route('/', methods=['GET'])
def get_posts():
    """Get all posts."""
    return jsonify({"message": "Get posts endpoint"}), 200

@posts_bp.route('/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """Get a specific post."""
    return jsonify({"message": f"Get post {post_id} endpoint"}), 200
