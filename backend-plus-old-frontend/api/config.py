from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings."""
    APP_NAME: str = "mini-api-v2"
    DEBUG: bool = True
    API_PREFIX: str = "/api"
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    class Config:
        case_sensitive = True

settings = Settings()
