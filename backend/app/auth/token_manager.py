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
    1. First, authenticate to Databricks using CLI auth (browser OAuth)
    2. Fetch SP credentials from Databricks secrets
    3. Use SP credentials to generate Lakebase database tokens
    4. Auto-refresh tokens before expiration (1 hour lifetime)
    
    This approach keeps SP credentials secure in Databricks secrets.
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

        self.secrets_scope = os.getenv("DATABRICKS_SECRETS_SCOPE")
        self.sp_client_id_key = os.getenv("SP_CLIENT_ID_KEY")
        self.sp_secret_key = os.getenv("SP_SECRET_KEY")
        
        self._workspace_client: Optional[WorkspaceClient] = None
        self._sp_client_id: Optional[str] = None
        self._sp_client_secret: Optional[str] = None
        
        self._init_workspace_client()
        self._fetch_sp_credentials()
        self.get_token() # Initial token fetch
        
        _log_info("LakebaseTokenManager initialized")
        _log_info(f"Workspace: {self.databricks_host}")
        _log_info(f"Instance: {self.lakebase_instance_name}")
        _log_info(f"Secrets scope: {self.secrets_scope}")
    
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
    
    def _fetch_sp_credentials(self):
        """Fetch Service Principal credentials from Databricks secrets."""
        import base64
        
        if not self._workspace_client:
            _log_warning("Cannot fetch SP credentials: WorkspaceClient not initialized.")
            return
        
        if not all([self.secrets_scope, self.sp_client_id_key, self.sp_secret_key]):
            _log_warning("Missing secrets configuration (scope/keys). Cannot fetch SP credentials.")
            return

        _log_info("Fetching SP credentials from secrets...")
        try:
            # Get raw secret values
            client_id_raw = self._workspace_client.secrets.get_secret(
                scope=self.secrets_scope, key=self.sp_client_id_key
            ).value
            client_secret_raw = self._workspace_client.secrets.get_secret(
                scope=self.secrets_scope, key=self.sp_secret_key
            ).value
            
            # Databricks secrets API returns base64-encoded values - decode them
            try:
                self._sp_client_id = base64.b64decode(client_id_raw).decode('utf-8')
            except Exception:
                # If decoding fails, use raw value (might already be plain text)
                self._sp_client_id = client_id_raw
                
            try:
                self._sp_client_secret = base64.b64decode(client_secret_raw).decode('utf-8')
            except Exception:
                # If decoding fails, use raw value
                self._sp_client_secret = client_secret_raw
            
            _log_info(f"SP credentials fetched. Client ID: {self._sp_client_id[:12] if self._sp_client_id else 'N/A'}...")
            _log_info(f"Secret length: {len(self._sp_client_secret) if self._sp_client_secret else 0}")
            
            # Update db_user to match SP client ID (ensures consistency)
            if self._sp_client_id:
                self.db_user = self._sp_client_id
                _log_info(f"Set DB_USER to SP client ID: {self.db_user}")
        except Exception as e:
            _log_warning(f"Failed to fetch secrets: {e}")
            self._sp_client_id = None
            self._sp_client_secret = None
    
    def _refresh_token(self):
        """Generate a new OAuth token using Service Principal or app identity."""
        if not self.lakebase_instance_name:
            _log_warning("Cannot refresh token: LAKEBASE_INSTANCE_NAME not set.")
            self._token = None
            self._expires_at = None
            return
        
        _log_info("Refreshing Lakebase OAuth token...")
        
        # Try Method 1: Use SP credentials from secrets (preferred for production)
        if self._sp_client_id and self._sp_client_secret:
            try:
                _log_info("Using SP credentials from secrets...")
                
                # Create Config with explicit M2M OAuth to prevent fallback to CLI auth
                from databricks.sdk.core import Config
                sp_config = Config(
                    host=self.databricks_host,
                    client_id=self._sp_client_id,
                    client_secret=self._sp_client_secret,
                    auth_type="oauth-m2m"  # Force M2M OAuth, prevent CLI auth fallback
                )
                sp_client = WorkspaceClient(config=sp_config)
                
                # Verify the identity before generating token
                try:
                    current_sp = sp_client.current_user.me()
                    _log_info(f"SP WorkspaceClient authenticated as: {current_sp.user_name}")
                except Exception as e:
                    _log_warning(f"Could not verify SP identity: {e}")
                
                credential = sp_client.database.generate_database_credential(
                    request_id=str(uuid.uuid4()),
                    instance_names=[self.lakebase_instance_name]
                )
                
                self._token = credential.token
                self._expires_at = datetime.fromisoformat(credential.expiration_time.replace('Z', '+00:00')) - timedelta(minutes=5)
                
                # CRITICAL: Update db_user to match the SP identity that generated the token
                # This ensures the DB connection uses the same identity as the token
                self.db_user = self._sp_client_id
                _log_info(f"Token refreshed via SP secrets. DB_USER set to: {self.db_user}")
                _log_info(f"Token expires at: {self._expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                return
            except Exception as e:
                _log_warning(f"SP secrets token generation failed: {e}")
        
        # Try Method 2: Use app's own identity (for Databricks Apps where app SP has DB access)
        if self._workspace_client:
            try:
                _log_info("Using app's own identity for database credential...")
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
                        _log_info(f"Updated DB_USER to app identity: {self.db_user}")
                except Exception:
                    pass
                
                _log_info(f"Token refreshed via app identity. Expires at: {self._expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                return
            except Exception as e:
                _log_error(f"App identity token generation failed: {e}")
        
        _log_error("All token generation methods failed.")
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
    """Initialize the token manager if OAuth is configured."""
    global token_manager
    
    # Check if OAuth is configured
    databricks_host = os.getenv("DATABRICKS_HOST")
    secrets_scope = os.getenv("DATABRICKS_SECRETS_SCOPE")
    
    if not databricks_host:
        raise Exception("DATABRICKS_HOST environment variable not set")
    if not secrets_scope:
        raise Exception("DATABRICKS_SECRETS_SCOPE environment variable not set")
    
    token_manager = LakebaseTokenManager()


# Initialize on module load (fault-tolerant)
try:
    init_token_manager()
except Exception as e:
    _log_error(f"Token manager initialization failed: {e}")
    _log_error("App will start but database operations will fail until auth is configured")

