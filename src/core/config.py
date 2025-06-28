"""
Core configuration module for VisaMate AI platform.
Handles environment variables, AWS services, and AI configurations.
"""

import os
from typing import List
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    """Application settings with environment variable defaults."""
    
    # Application Configuration
    APP_NAME: str = "VisaMate AI"
    API_VERSION: str = "v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "info"
    
    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    
    # AWS Cognito Configuration
    COGNITO_USER_POOL_ID: str = ""
    COGNITO_CLIENT_ID: str = ""
    COGNITO_CLIENT_SECRET: str = ""
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AWS RDS Configuration (Free Tier)
    RDS_ENDPOINT: str = ""
    RDS_DATABASE: str = "visamate"
    RDS_USERNAME: str = "admin"
    RDS_PASSWORD: str = ""
    RDS_PORT: int = 5432
    DATABASE_URL: str = "postgresql://admin:password@localhost:5432/visamate"
    
    # AWS DynamoDB Configuration (Free Tier)
    DYNAMODB_TABLE_PREFIX: str = "visamate"
    DYNAMODB_REGION: str = "us-east-1"
    
    # AWS S3 Configuration (Free Tier)
    S3_BUCKET_NAME: str = "visamate-documents"
    S3_REGION: str = "us-east-1"
    
    # AWS Lambda Configuration
    LAMBDA_FUNCTION_PREFIX: str = "visamate"
    
    # Google Gemini AI Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MAX_TOKENS: int = 8192
    
    # Fallback AI Configuration
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gemini-1.5-pro"
    
    # Vector Database (Free Tier alternatives)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    
    # Redis Configuration (AWS ElastiCache Free Tier)
    REDIS_URL: str = "redis://localhost:6379"
    ELASTICACHE_ENDPOINT: str = ""
    
    # WhatsApp Integration
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    
    # Payment Integration
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # External APIs
    IRCC_API_ENDPOINT: str = "https://api.ircc.ca"
    PROVINCIAL_API_ENDPOINT: str = "https://api.provincial.ca"
    
    # Localization
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: List[str] = None  # type: ignore
    
    # Security
    ENCRYPTION_KEY: str = "your-32-character-encryption-key"
    CORS_ORIGINS: List[str] = None  # type: ignore
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # SOP Generation Configuration
    SOP_MIN_WORDS: int = 800
    SOP_MAX_WORDS: int = 1500
    SOP_TARGET_READABILITY: float = 60.0  # Flesch Reading Ease score
    
    # Document Processing
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = None  # type: ignore
    
    # Monitoring and Analytics
    SENTRY_DSN: str = ""
    GOOGLE_ANALYTICS_ID: str = ""
    
    def __post_init__(self):
        """Load environment variables after initialization."""
        if self.SUPPORTED_LANGUAGES is None:
            self.SUPPORTED_LANGUAGES = ["en", "pa", "gu", "hn"]
        if self.CORS_ORIGINS is None:
            self.CORS_ORIGINS = ["http://localhost:3000", "http://localhost:8080"]
        if self.ALLOWED_FILE_TYPES is None:
            self.ALLOWED_FILE_TYPES = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
        
        # Load from environment variables
        for field_name in self.__dataclass_fields__:
            env_value = os.getenv(field_name)
            if env_value is not None:
                field_type = self.__dataclass_fields__[field_name].type
                if field_type == bool:
                    setattr(self, field_name, env_value.lower() in ('true', '1', 'yes'))
                elif field_type == int:
                    setattr(self, field_name, int(env_value))
                elif field_type == float:
                    setattr(self, field_name, float(env_value))
                elif field_type == List[str]:
                    setattr(self, field_name, [s.strip() for s in env_value.split(',')])
                else:
                    setattr(self, field_name, env_value)
        
        # Construct DATABASE_URL if RDS components are provided
        if self.RDS_ENDPOINT and self.RDS_PASSWORD:
            self.DATABASE_URL = f"postgresql://{self.RDS_USERNAME}:{self.RDS_PASSWORD}@{self.RDS_ENDPOINT}:{self.RDS_PORT}/{self.RDS_DATABASE}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings() 