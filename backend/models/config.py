"""
Configuration models and settings.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None  # For temporary credentials
    aws_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    max_tokens: int = 4000  # Increased for full code responses
    temperature: float = 0.7
    github_token: Optional[str] = None
    log_level: str = "INFO"
    enable_bedrock: bool = True  # Enable Bedrock for AI analysis
    
    # DynamoDB Configuration
    dynamodb_endpoint_url: Optional[str] = None # Set to "http://localhost:1234" for local DynamoDB
    use_local_dynamodb: bool = False # Set to True to use local DynamoDB
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields instead of raising errors
