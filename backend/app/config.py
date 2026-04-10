"""Application configuration settings."""
import os
import logging
from urllib.parse import quote_plus
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment: "local", "development", "production"
    environment: str = "local"
    
    # Log level: DEBUG, INFO, WARNING, ERROR
    log_level: str = "INFO"
    
    # Lakebase Database Configuration
    db_host: str = ""
    db_user: str = ""
    db_name: str = "lakemeter_pricing"
    db_port: int = 5432
    db_sslmode: str = "require"
    
    # Databricks configuration
    # In Databricks Apps: DATABRICKS_HOST, DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET
    # are auto-injected. The app's built-in SP handles all authentication.
    databricks_host: Optional[str] = None
    databricks_config_profile: Optional[str] = None
    
    # Lakebase instance name (from Compute > Lakebase Postgres)
    lakebase_instance_name: Optional[str] = None
    
    # Override with full DATABASE_URL if provided
    database_url: Optional[str] = None
    
    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:5175"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list. Empty string means same-origin only."""
        if not self.cors_origins or self.cors_origins.strip() == "":
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def use_oauth(self) -> bool:
        """Check if OAuth authentication is configured (Databricks Apps auto-injects host)."""
        return bool(self.databricks_host)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_local(self) -> bool:
        """Check if running in local development."""
        return self.environment.lower() == "local"
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging():
    """Configure logging based on environment."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    if settings.is_production:
        # Production: minimal logging, only warnings and errors
        logging.basicConfig(
            level=logging.WARNING,
            format=log_format
        )
    else:
        # Local/Development: verbose logging
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format=log_format
        )
    
    # Suppress noisy third-party loggers in production
    if settings.is_production:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with environment-aware settings."""
    return logging.getLogger(name)


# Helper for conditional logging (backwards compatible with print statements)
def log_debug(message: str, logger_name: str = "lakemeter"):
    """Log debug message (only in local/dev)."""
    if not settings.is_production:
        get_logger(logger_name).debug(message)


def log_info(message: str, logger_name: str = "lakemeter"):
    """Log info message (only in local/dev)."""
    if not settings.is_production:
        get_logger(logger_name).info(message)


def log_warning(message: str, logger_name: str = "lakemeter"):
    """Log warning message (always)."""
    get_logger(logger_name).warning(message)


def log_error(message: str, logger_name: str = "lakemeter"):
    """Log error message (always)."""
    get_logger(logger_name).error(message)
