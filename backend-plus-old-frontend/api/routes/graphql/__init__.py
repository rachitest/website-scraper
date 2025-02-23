from flask import Blueprint
from .schema import schema

graphql_bp = Blueprint('graphql', __name__)

def register_graphql_routes(app):
    """Register GraphQL routes."""
    from strawberry.flask.views import GraphQLView
    
    # Register the GraphQL view
    app.add_url_rule(
        "/graphql",
        view_func=GraphQLView.as_view("graphql_view", schema=schema)
    )
