import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def validate_url(url):
    """Validate URL format"""
    try:
        # Add https:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'

        result = urlparse(url)
        # Check for valid domain with TLD
        if '.' not in result.netloc:
            return False
        
        return bool(result.netloc)
    except Exception as e:
        logger.error(f"URL validation error: {str(e)}")
        return False

def normalize_url(url):
    """Normalize URL format"""
    if not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url 