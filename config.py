"""
Configuration management for Letterboxd Movie Recommender Bot.
Loads environment variables and provides centralized config access.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class."""
    
    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    TMDB_API_KEY = os.getenv("TMDB_API_KEY")
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # TMDB Configuration
    TMDB_BASE_URL = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
    TMDB_RATE_LIMIT = 40  # requests per 10 seconds
    
    # Claude Configuration
    CLAUDE_MODEL = "claude-3-5-haiku-20241022"  # Fast, cheap, and capable!
    CLAUDE_MAX_TOKENS = 1024
    CLAUDE_TEMPERATURE = 1.0
    
    # Application Settings
    MIN_MOVIES_REQUIRED = 5  # Minimum movies needed to generate recommendations
    RECOMMENDATIONS_COUNT = 10  # Number of recommendations to generate
    REQUEST_TIMEOUT = 30  # seconds
    
    # Cache Settings
    ENABLE_CACHE = True
    CACHE_TTL = 3600  # Time-to-live in seconds (1 hour)
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        errors = []
        
        if not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY is not set in .env file")
        
        if not cls.TMDB_API_KEY:
            errors.append("TMDB_API_KEY is not set in .env file")
        
        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        
        return True


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"\n⚠️  {e}\n")
    print("Please create a .env file with your API keys.")
    print("See .env.example for the required format.\n")
