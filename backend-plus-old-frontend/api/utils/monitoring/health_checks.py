import os
import logging
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

def get_partial_response(url, reason="API not configured"):
    """Generate a graceful partial response when services are unavailable"""
    response_data = {
        "url": url,
        "analysis": f"OpenAI analysis not available - {reason}",
        "status": "partial",
        # Add minimal organization data to prevent frontend errors
        "organization": {
            "name": "Analysis Limited",
            "type": "Partial Analysis",
            "location": "N/A",
            "industry": "N/A"
        }
    }
    logger.info(f"Returning partial response: {response_data}")
    return response_data

def check_openai_status():
    """Check OpenAI API configuration and status"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found in environment variables")
        return {
            "status": "unconfigured",
            "message": "OpenAI API key not configured"
        }
    
    try:
        client = OpenAI(api_key=api_key)
        return {
            "status": "configured",
            "client": client,
            "message": "OpenAI API configured successfully"
        }
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
        return {
            "status": "error",
            "message": f"OpenAI API configuration error: {str(e)}"
        }

def check_database_status():
    """Check database configuration and connectivity"""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL not found in environment variables")
        return {
            "status": "unconfigured",
            "message": "Database URL not configured"
        }
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.warning(f"Database health check failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Database connection error: {str(e)}"
        } 