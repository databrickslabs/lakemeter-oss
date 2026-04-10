"""
Database connection and session management.

Supports automatic OAuth token refresh for Lakebase using Service Principal M2M flow.
Reference: https://docs.databricks.com/aws/en/oltp/instances/authentication
"""
import threading
import time
from urllib.parse import quote_plus

from fastapi import HTTPException
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from app.config import log_info, log_warning, log_error


# Base class for models (defined early so models can import it)
Base = declarative_base()


def _get_database_url() -> str:
    """Build database URL from env var, token manager, or secrets fallback."""
    import os

    # Check for direct DATABASE_URL first (local dev)
    direct_url = os.getenv("DATABASE_URL")
    if direct_url:
        log_info("Using DATABASE_URL environment variable for database connection")
        return direct_url

    from app.auth.token_manager import token_manager

    # Try OAuth token manager if it has a valid token
    if token_manager and token_manager.get_token():
        params = token_manager.get_connection_params()
        if params.get("password"):
            # Test SP connection before committing — fast timeout to avoid blocking
            try:
                encoded_user = quote_plus(params["user"])
                encoded_password = quote_plus(params["password"])
                test_url = (
                    f"postgresql://{encoded_user}:{encoded_password}"
                    f"@{params['host']}:{params['port']}/{params['dbname']}"
                    f"?sslmode={params['sslmode']}"
                )
                test_engine = create_engine(
                    test_url,
                    connect_args={"sslmode": "require", "connect_timeout": 5},
                    pool_timeout=5,
                )
                with test_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                test_engine.dispose()
                log_info(f"Using OAuth SP token for database connection (user: {params['user']})")
                return test_url
            except Exception as e:
                log_warning(f"SP OAuth connection test failed: {e}")
                log_info("Falling back to password auth...")
    else:
        log_info("No SP OAuth credentials available, using password fallback...")

    # Fallback: use secrets-based password auth (lakebase-password from secrets scope)
    log_info("Attempting password-based auth via Databricks secrets...")
    try:
        from databricks.sdk import WorkspaceClient
        import base64
        w = WorkspaceClient()
        scope = os.getenv("DATABRICKS_SECRETS_SCOPE", "lakemeter-credentials")

        def _get_secret(key):
            raw = w.secrets.get_secret(scope=scope, key=key).value
            try:
                return base64.b64decode(raw).decode('utf-8')
            except Exception:
                return raw

        db_host = _get_secret("lakebase-host")
        db_user = _get_secret("lakebase-user")
        db_pass = _get_secret("lakebase-password")
        db_name = _get_secret("lakebase-database")
        db_port = os.getenv("DB_PORT", "5432")

        encoded_user = quote_plus(db_user)
        encoded_password = quote_plus(db_pass)
        log_info(f"Using password auth for user: {db_user}")
        return (
            f"postgresql://{encoded_user}:{encoded_password}"
            f"@{db_host}:{db_port}/{db_name}"
            f"?sslmode=require"
        )
    except Exception as e:
        log_error(f"Password fallback failed: {e}")

    raise Exception("No valid database credentials available. Check OAuth config or lakebase-password secret.")


def _create_engine_with_token_refresh():
    """Create SQLAlchemy engine with automatic token refresh."""
    try:
        database_url = _get_database_url()
    except Exception as e:
        log_error(f"Database initialization failed: {e}")
        raise
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=15,
            max_overflow=25,
            pool_timeout=15,
            # Recycle connections every 15 minutes (before token expires at 1 hour)
            pool_recycle=900,
            connect_args={"sslmode": "require", "connect_timeout": 10}
        )
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        log_info("Database engine created for Lakebase")
        
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return engine, session_local
        
    except Exception as e:
        log_error(f"Could not create database engine: {e}")
        raise


# Initialize engine and session factory (fault-tolerant)
try:
    engine, SessionLocal = _create_engine_with_token_refresh()
except Exception as e:
    log_error(f"Database initialization failed (will retry on first request): {e}")
    engine = None
    SessionLocal = None


# Track last engine refresh time
_last_engine_refresh = time.time()
_ENGINE_REFRESH_INTERVAL = 30 * 60  # Refresh engine every 30 minutes (well before 1-hour token expiry)
_refresh_lock = threading.Lock()


def refresh_engine():
    """Refresh the database engine with a new token. Thread-safe."""
    global engine, SessionLocal, _last_engine_refresh
    
    from app.auth.token_manager import token_manager
    
    with _refresh_lock:
        log_info("Refreshing database engine with new token...")
        
        if token_manager:
            # Force token refresh
            token_manager._token = None
            token_manager._expires_at = None
        
        try:
            engine, SessionLocal = _create_engine_with_token_refresh()
            _last_engine_refresh = time.time()
            log_info("Database engine refreshed successfully")
            return True
        except Exception as e:
            log_error(f"Failed to refresh database engine: {e}")
            return False


def _check_and_refresh_engine():
    """Check if engine needs refresh due to token age."""
    global engine, SessionLocal, _last_engine_refresh
    
    # If engine is None, try to create it
    if engine is None:
        log_info("Engine is None, attempting to create...")
        try:
            refresh_engine()
        except Exception as e:
            log_error(f"Failed to create engine: {e}")
            return False
    
    # Check if it's time to refresh (proactive refresh before token expires)
    time_since_refresh = time.time() - _last_engine_refresh
    if time_since_refresh > _ENGINE_REFRESH_INTERVAL:
        log_info(f"Engine is {time_since_refresh/60:.1f} minutes old, proactively refreshing...")
        refresh_engine()
    
    return engine is not None


def get_db():
    """
    Dependency to get database session.
    
    Automatically handles token refresh on connection errors.
    """
    # Proactive refresh check
    _check_and_refresh_engine()
    
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    db = SessionLocal()
    try:
        # Test the connection before yielding
        try:
            db.execute(text("SELECT 1"))
        except OperationalError as e:
            error_str = str(e).lower()
            # Check if it's an auth/token error
            if "invalid authorization" in error_str or "authentication failed" in error_str or "password" in error_str:
                log_warning("Database connection failed due to auth error, refreshing token...")
                db.close()
                
                # Refresh engine with new token
                if refresh_engine():
                    # Retry with new session
                    db = SessionLocal()
                    db.execute(text("SELECT 1"))  # Test again
                else:
                    raise HTTPException(status_code=503, detail="Database connection failed after token refresh")
            else:
                raise
        
        yield db
    except OperationalError as e:
        error_str = str(e).lower()
        if "invalid authorization" in error_str or "authentication failed" in error_str:
            log_warning("Database operation failed due to auth error, refreshing for next request...")
            refresh_engine()
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")
    finally:
        db.close()
