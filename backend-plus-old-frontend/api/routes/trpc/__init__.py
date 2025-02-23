from flask import Blueprint

trpc_bp = Blueprint('trpc', __name__)

def register_trpc_routes(app):
    """Register tRPC routes."""
    # tRPC route registration will be implemented here
    app.register_blueprint(trpc_bp, url_prefix='/trpc')
