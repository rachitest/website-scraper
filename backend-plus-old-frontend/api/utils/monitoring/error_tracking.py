from typing import Optional
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask, Response
import os
import logging

logger = logging.getLogger(__name__)

def init_error_tracking(app: Flask, dsn: Optional[str] = None) -> None:
    """
    Initialize error tracking with GlitchTip/Sentry SDK
    
    Args:
        app: Flask application instance
        dsn: GlitchTip DSN string. If None, error tracking will be disabled.
    """
    if not dsn:
        logger.warning("No DSN provided for error tracking. Error tracking is disabled.")
        return
        
    environment = os.environ.get('FLASK_ENV', 'development')
    
    try:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            environment=environment,
            # Disable performance monitoring to focus on errors
            traces_sample_rate=1.0,
            # Disable debug mode to reduce noise
            debug=False,
            send_default_pii=True
        )
        logger.info(f"Error tracking initialized for environment: {environment}")
        
    except Exception as e:
        logger.error(f"Failed to initialize error tracking: {str(e)}")
        return
    
    @app.route('/debug-glitchtip')
    def trigger_error() -> Response:
        # Explicitly capture message before error
        sentry_sdk.capture_message("Triggering test error", level="error")
        raise ZeroDivisionError("Test error triggered via /debug-glitchtip") 