from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://securepay:securepay@localhost:5432/securepayai"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    
    # Claude API (optional)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-haiku-20241022"
    
    # Fraud engine parameters
    fraud_amount_multiplier: float = 5.0
    fraud_night_start_hour: int = 0
    fraud_night_end_hour: int = 5
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 3
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
