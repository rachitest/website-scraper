from typing import Optional, Dict, Any, Union, Tuple
from flask import Flask, render_template, jsonify, Request, request, redirect, url_for
from werkzeug.wrappers import Response
import traceback
import logging
from werkzeug.exceptions import HTTPException
import sentry_sdk
from uuid import uuid4

logger = logging.getLogger(__name__)

def init_error_handlers(app: Flask) -> None:
    """Initialize error handlers for the Flask application."""
    
    def is_api_request(request: Request) -> bool:
        """Check if the request is an API request based on path or Accept header."""
        return (
            request.path.startswith('/api/') or
            request.headers.get('Accept', '').lower().startswith('application/json')
        )

    @app.route('/submit_error_feedback', methods=['POST'])
    def submit_error_feedback() -> Response:
        """Handle error feedback form submissions."""
        error_id = request.form.get('error_id')
        error_code = request.form.get('error_code')
        email = request.form.get('email')
        message = request.form.get('message')

        # Capture feedback with Sentry
        with sentry_sdk.push_scope() as scope:
            scope.set_extra('error_id', error_id)
            scope.set_extra('error_code', error_code)
            scope.set_extra('user_email', email)
            scope.set_user({'email': email} if email else None)
            
            sentry_sdk.capture_message(
                f"Error Feedback: {message}",
                level="info"
            )

        # Redirect back with a success message
        return redirect(url_for('index'))

    @app.errorhandler(Exception)
    def handle_exception(error: Exception) -> Tuple[Union[Response, str], int]:
        """Handle any uncaught exception."""
        # Generate a unique error ID for tracking
        error_id = str(uuid4())
        
        # Get the error details
        if isinstance(error, HTTPException):
            status_code = error.code or 500
            error_message = error.description
        else:
            status_code = 500
            error_message = str(error)
        
        # Log the full error with traceback
        logger.error(
            f"Error {status_code} [{error_id}]: {error_message}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        
        # Set error context for Sentry
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag('error_id', error_id)
            scope.set_extra('error_code', status_code)
            scope.set_extra('error_message', error_message)
        
        # Different responses for API vs Web requests
        if is_api_request(request):
            return jsonify({
                'error': error_message,
                'status_code': status_code,
                'error_id': error_id
            }), status_code
        
        # Web response with error page
        return render_template(
            'error.html',
            error_id=error_id,
            error_title=get_error_title(status_code),
            error_message=get_user_message(status_code, error_message),
            error_code=status_code,
            show_retry=status_code in [408, 429, 503]  # Show retry for timeout/rate-limit/maintenance
        ), status_code

    @app.errorhandler(404)
    def not_found_error(error: Exception) -> Tuple[Union[Response, str], int]:
        """Handle 404 errors specifically."""
        error_id = str(uuid4())
        
        if is_api_request(request):
            return jsonify({
                'error': 'Resource not found',
                'status_code': 404,
                'error_id': error_id
            }), 404
            
        return render_template(
            'error.html',
            error_id=error_id,
            error_title='Page Not Found',
            error_message='The page you are looking for does not exist.',
            error_code=404,
            show_retry=False
        ), 404

    @app.errorhandler(429)
    def ratelimit_error(error: Exception) -> Tuple[Union[Response, str], int]:
        """Handle rate limit errors specifically."""
        error_id = str(uuid4())
        
        if is_api_request(request):
            return jsonify({
                'error': 'Too many requests',
                'status_code': 429,
                'error_id': error_id
            }), 429
            
        return render_template(
            'error.html',
            error_id=error_id,
            error_title='Too Many Requests',
            error_message='Please wait a moment before trying again.',
            error_code=429,
            show_retry=True
        ), 429

def get_error_title(status_code: int) -> str:
    """Get a user-friendly error title based on status code."""
    titles = {
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Page Not Found',
        408: 'Request Timeout',
        429: 'Too Many Requests',
        500: 'Server Error',
        502: 'Bad Gateway',
        503: 'Service Unavailable',
        504: 'Gateway Timeout'
    }
    return titles.get(status_code, 'Unexpected Error')

def get_user_message(status_code: int, error_message: Optional[str] = None) -> str:
    """Get a user-friendly error message based on status code."""
    messages = {
        400: 'The request could not be understood. Please check your input and try again.',
        401: 'Please log in to access this resource.',
        403: 'You do not have permission to access this resource.',
        404: 'The page you are looking for could not be found.',
        408: 'The request took too long to complete. Please try again.',
        429: 'Too many requests. Please wait a moment before trying again.',
        500: 'An unexpected error occurred. Our team has been notified.',
        502: 'The server received an invalid response. Please try again later.',
        503: 'The service is temporarily unavailable. Please try again later.',
        504: 'The server took too long to respond. Please try again later.'
    }
    
    if status_code in [400, 401, 403] and error_message:
        return error_message  # Use specific error message for client errors
        
    return messages.get(status_code, 'An unexpected error occurred. Our team has been notified.') 