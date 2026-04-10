"""
Lakebase OAuth Token Manager

Uses Databricks Service Principal OAuth (M2M) to generate and refresh
database credentials for Lakebase authentication.

Supports fetching SP credentials from Databricks secrets for enhanced security.

Reference: https://docs.databricks.com/aws/en/oltp/instances/authentication
"""
import os
import uuid
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import logging helpers (defined inline to avoid circular import)
def _log_info(msg: str):
    """Log info - only in local/dev mode."""
    if os.getenv("ENVIRONMENT", "local").lower() != "production":
        print(f"[TokenManager] {msg}")

def _log_warning(msg: str):
    """Log warning - always."""
    print(f"[TokenManager] WARNING: {msg}")

def _log_error(msg: str):
    """Log error - always."""
    print(f"[TokenManager] ERROR: {msg}")


class LakebaseTokenManager:
    """
    Manages OAuth tokens for Lakebase database authentication.

    Authentication flow:
    1. Authenticate to Databricks using the app's built-in Service Principal
       (DATABRICKS_CLIENT_ID/DATABRICKS_CLIENT_SECRET auto-injected by Databricks Apps)
       or CLI auth (local development)
    2. Use generate_database_credential to get a Lakebase OAuth token
    3. Auto-refresh tokens before expiration (1 hour lifetime)
    """

    def __init__(self):
        self._token: Optional[str] = None
        self._expires_at: Optional[datetime] = None
        self._lock = threading.Lock()

        # Load settings from environment variables
        self.databricks_host = os.getenv("DATABRICKS_HOST")
        self.databricks_config_profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        self.lakebase_instance_name = os.getenv("LAKEBASE_INSTANCE_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_name = os.getenv("DB_NAME")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = int(os.getenv("DB_PORT", "5432"))
        self.db_sslmode = os.getenv("DB_SSLMODE", "require")

        self._workspace_client: Optional[WorkspaceClient] = None

        self._init_workspace_client()
        self.get_token() # Initial token fetch

        _log_info("LakebaseTokenManager initialized")
        _log_info(f"Workspace: {self.databricks_host}")
        _log_info(f"Instance: {self.lakebase_instance_name}")
    
    def _init_workspace_client(self):
        """Initialize Databricks WorkspaceClient using available auth."""
        try:
            if self.databricks_config_profile:
                # Local dev: use CLI profile
                config = Config(
                    host=self.databricks_host,
                    profile=self.databricks_config_profile
                )
                self._workspace_client = WorkspaceClient(config=config)
            else:
                # Production/Databricks Apps: try no-args first (auto-detects app SP)
                try:
                    self._workspace_client = WorkspaceClient()
                    current_user = self._workspace_client.current_user.me()
                    _log_info(f"Authenticated (auto) as: {current_user.user_name}")
                    return
                except Exception as e1:
                    _log_warning(f"Auto auth failed: {e1}, trying with explicit host...")
                    # Fallback: explicit host (ensure https://)
                    host = self.databricks_host
                    if host and not host.startswith("https://"):
                        host = f"https://{host}"
                    self._workspace_client = WorkspaceClient(host=host)

            # Test auth by getting current user
            current_user = self._workspace_client.current_user.me()
            _log_info(f"Authenticated as: {current_user.user_name}")
        except Exception as e:
            _log_warning(f"Auth failed: {e}")
            self._workspace_client = None
    
    def _refresh_token(self):
        """Generate a new OAuth token using the app's built-in identity."""
        if not self.lakebase_instance_name:
            _log_warning("Cannot refresh token: LAKEBASE_INSTANCE_NAME not set.")
            self._token = None
            self._expires_at = None
            return

        if not self._workspace_client:
            _log_error("Cannot refresh token: WorkspaceClient not initialized.")
            self._token = None
            self._expires_at = None
            return

        _log_info("Refreshing Lakebase OAuth token...")
        try:
            credential = self._workspace_client.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[self.lakebase_instance_name]
            )

            self._token = credential.token
            self._expires_at = datetime.fromisoformat(credential.expiration_time.replace('Z', '+00:00')) - timedelta(minutes=5)

            # Update db_user to match the app's SP identity
            try:
                current_user = self._workspace_client.current_user.me()
                if current_user.user_name:
                    self.db_user = current_user.user_name
                    _log_info(f"DB_USER set to app identity: {self.db_user}")
            except Exception:
                pass

            _log_info(f"Token refreshed. Expires at: {self._expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        except Exception as e:
            _log_error(f"Token generation failed: {e}")
            self._token = None
            self._expires_at = None
    
    def get_token(self) -> Optional[str]:
        """
        Returns the current valid OAuth token, refreshing it if it's expired or near expiration.
        Thread-safe.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            if not self._token or (self._expires_at and now >= self._expires_at):
                self._refresh_token()
            return self._token
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Returns database connection parameters, including the current token as password."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "user": self.db_user,
            "password": self.get_token(), # Use the dynamically refreshed token
            "dbname": self.db_name,
            "sslmode": self.db_sslmode
        }


# Initialize token manager (will be None if not configured)
token_manager: Optional[LakebaseTokenManager] = None

def init_token_manager():
    """Initialize the token manager if Databricks host is configured."""
    global token_manager

    databricks_host = os.getenv("DATABRICKS_HOST")
    if not databricks_host:
        raise Exception("DATABRICKS_HOST environment variable not set")

    token_manager = LakebaseTokenManager()


# Initialize on module load (fault-tolerant)
try:
    init_token_manager()
except Exception as e:
    _log_error(f"Token manager initialization failed: {e}")
    _log_error("App will start but database operations will fail until auth is configured")

