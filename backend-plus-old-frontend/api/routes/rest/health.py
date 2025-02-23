from flask import Blueprint, jsonify
from typing import Dict

router = Blueprint('health', __name__)

@router.route('/health', methods=['GET'])
def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict[str, str]: A dictionary containing the health status and version
    """
    return jsonify({
        "status": "healthy",
        "version": "1.0.0"
    })