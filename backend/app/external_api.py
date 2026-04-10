"""
External Lakemeter API Client

This module provides an async HTTP client for calling the external Lakemeter API.

Authentication methods (in order of priority):
1. X-Forwarded-Access-Token header (production - Databricks Apps)
2. Databricks CLI auth (local development - uses browser OAuth)

For local development, ensure you have Databricks CLI configured:
  databricks auth login --host <your-workspace-url>
"""
import os
import httpx
from typing import Optional, Dict, Any
from fastapi import Request
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config

from app.config import log_info, log_warning

# External API base URL
LAKEMETER_API_BASE = "https://lakemeter-api-335310294452632.aws.databricksapps.com"

# Header name for OAuth token in Databricks Apps
ACCESS_TOKEN_HEADER = "X-Forwarded-Access-Token"

# Cache for CLI config (not the token - SDK handles token refresh)
_cli_config: Optional[Config] = None


def get_cli_token() -> Optional[str]:
    """
    Get Databricks API token using CLI authentication.
    
    This uses the Databricks CLI's cached OAuth token from browser authentication.
    The Databricks SDK handles token refresh automatically.
    Requires: databricks auth login --host <workspace-url>
    """
    global _cli_config
    
    try:
        databricks_host = os.getenv("DATABRICKS_HOST")
        databricks_profile = os.getenv("DATABRICKS_CONFIG_PROFILE")
        
        if not databricks_host:
            log_warning("DATABRICKS_HOST not set, cannot get CLI token")
            return None
        
        # Initialize config once (SDK handles token caching and refresh)
        if not _cli_config:
            _cli_config = Config(
                host=databricks_host,
                profile=databricks_profile
            )
            log_info(f"Initialized Databricks CLI config for {databricks_host}")
        
        # authenticate() returns fresh headers each time, including refreshed tokens
        auth_headers = _cli_config.authenticate()
        
        if auth_headers:
            auth_header = auth_headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                return auth_header[7:]  # Remove 'Bearer ' prefix
                
    except Exception as e:
        log_warning(f"Could not get CLI token: {e}")
        # Clear config cache on error so it re-initializes next time
        _cli_config = None
    
    return None


def get_sp_token() -> Optional[str]:
    """
    Get the app's built-in Service Principal token.
    In Databricks Apps, DATABRICKS_CLIENT_ID/DATABRICKS_CLIENT_SECRET are auto-injected.
    """
    try:
        from app.auth.token_manager import token_manager
        if token_manager and token_manager._workspace_client:
            auth_headers = token_manager._workspace_client.config.authenticate()
            if auth_headers:
                auth_header = auth_headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    return auth_header[7:]
    except Exception as e:
        log_warning(f"Could not get SP token: {e}")
    return None


def get_user_token(request: Request) -> Optional[str]:
    """
    Get user's OAuth token for external API authentication.

    Priority:
    1. X-Forwarded-Access-Token header (Databricks Apps production - if available)
    2. Service Principal token (Databricks Apps - using same SP as Lakebase auth)
    3. Databricks CLI token (local development)
    """
    # First try production header (may not always be available)
    token = request.headers.get(ACCESS_TOKEN_HEADER)
    if token:
        log_info("Using X-Forwarded-Access-Token for external API")
        return token

    # Try Service Principal token (for Databricks Apps without user token)
    sp_token = get_sp_token()
    if sp_token:
        log_info("Using Service Principal token for external API")
        return sp_token

    # Fall back to CLI token for local development
    cli_token = get_cli_token()
    if cli_token:
        log_info("Using CLI token for external API")
        return cli_token

    log_warning("No token available for external API calls")
    return None


def get_model_serving_token(request: Request) -> Optional[str]:
    """
    Get token for model serving (Claude AI) calls.

    Uses the app's own credentials (SP or CLI) instead of the user's forwarded token,
    because the Databricks Apps proxy may strip the model-serving scope from user tokens.
    The serving endpoint resource (CAN_QUERY) is granted to the app's service principal.

    Priority:
    1. Service Principal token (Databricks Apps production)
    2. Databricks CLI token (local development)
    3. X-Forwarded-Access-Token (fallback)
    """
    # Prefer SP token — it has model-serving scope via app resource config
    sp_token = get_sp_token()
    if sp_token:
        log_info("Using Service Principal token for model serving")
        return sp_token

    # Fall back to CLI token for local development
    cli_token = get_cli_token()
    if cli_token:
        log_info("Using CLI token for model serving")
        return cli_token

    # Last resort: user's forwarded token
    token = request.headers.get(ACCESS_TOKEN_HEADER)
    if token:
        log_info("Using X-Forwarded-Access-Token for model serving (may lack scope)")
        return token

    log_warning("No token available for model serving calls")
    return None


async def call_external_api(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    user_token: Optional[str] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Make an authenticated call to the external Lakemeter API.
    
    Args:
        endpoint: API endpoint path (e.g., "/api/v1/regions")
        method: HTTP method (GET, POST, etc.)
        params: Query parameters for GET requests
        json_body: JSON body for POST requests
        user_token: OAuth token from Databricks Apps
        timeout: Request timeout in seconds
    
    Returns:
        API response as dictionary
    
    Raises:
        Exception if API call fails and no token available
    """
    headers = {"Accept": "application/json"}
    
    if user_token:
        headers["Authorization"] = f"Bearer {user_token}"
    
    url = f"{LAKEMETER_API_BASE}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        if method.upper() == "GET":
            response = await client.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
        elif method.upper() == "POST":
            headers["Content-Type"] = "application/json"
            response = await client.post(
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=timeout
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()


class LakemeterAPIClient:
    """
    Client for external Lakemeter API with user token authentication.
    """
    
    def __init__(self, user_token: Optional[str] = None):
        self.user_token = user_token
    
    async def get_clouds(self) -> Dict[str, Any]:
        """Get available cloud providers."""
        return await call_external_api(
            "/api/v1/clouds",
            user_token=self.user_token
        )
    
    async def get_regions(self, cloud: str) -> Dict[str, Any]:
        """Get regions for a cloud provider."""
        return await call_external_api(
            "/api/v1/regions",
            params={"cloud": cloud.upper()},
            user_token=self.user_token
        )
    
    async def get_pricing_tiers(self, cloud: str) -> Dict[str, Any]:
        """Get available pricing tiers for a cloud."""
        return await call_external_api(
            "/api/v1/pricing-tiers",
            params={"cloud": cloud.upper()},
            user_token=self.user_token
        )
    
    async def get_instance_types(
        self, 
        cloud: str, 
        region: Optional[str] = None,
        min_vcpus: Optional[int] = None,
        max_vcpus: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get available instance types."""
        params = {"cloud": cloud.upper()}
        if region:
            params["region"] = region
        if min_vcpus:
            params["min_vcpus"] = min_vcpus
        if max_vcpus:
            params["max_vcpus"] = max_vcpus
        
        return await call_external_api(
            "/api/v1/instances/types",
            params=params,
            user_token=self.user_token
        )
    
    async def get_vm_costs(
        self,
        cloud: str,
        region: str,
        instance_type: Optional[str] = None,
        pricing_tier: Optional[str] = None,
        payment_option: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get VM costs for instances."""
        params = {"cloud": cloud.upper(), "region": region}
        if instance_type:
            params["instance_type"] = instance_type
        if pricing_tier:
            params["pricing_tier"] = pricing_tier
        if payment_option:
            params["payment_option"] = payment_option
        
        return await call_external_api(
            "/api/v1/instances/vm-costs",
            params=params,
            user_token=self.user_token
        )
    
    async def get_instance_families(self) -> Dict[str, Any]:
        """Get instance family categories."""
        return await call_external_api(
            "/api/v1/instances/families",
            user_token=self.user_token
        )
    
    async def get_dbsql_warehouse_sizes(self) -> Dict[str, Any]:
        """Get DBSQL warehouse sizes."""
        return await call_external_api(
            "/api/v1/dbsql/warehouse-sizes",
            user_token=self.user_token
        )
    
    async def get_gpu_types(self, cloud: str) -> Dict[str, Any]:
        """Get GPU types for model serving."""
        return await call_external_api(
            "/api/v1/model-serving/gpu-types",
            params={"cloud": cloud.upper()},
            user_token=self.user_token
        )
    
    async def get_fmapi_databricks_models(self) -> Dict[str, Any]:
        """Get Databricks FMAPI models."""
        return await call_external_api(
            "/api/v1/fmapi/databricks-models/list",
            user_token=self.user_token
        )
    
    async def get_fmapi_proprietary_models(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get proprietary FMAPI models."""
        params = {}
        if provider:
            params["provider"] = provider
        
        return await call_external_api(
            "/api/v1/fmapi/proprietary-models/list",
            params=params,
            user_token=self.user_token
        )
    
    # ==================== Cost Calculation Methods ====================
    
    async def calculate_jobs_classic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate JOBS classic cost."""
        return await call_external_api(
            "/api/v1/calculate/jobs-classic",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_jobs_serverless(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate JOBS serverless cost."""
        return await call_external_api(
            "/api/v1/calculate/jobs-serverless",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_all_purpose_classic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate All-Purpose classic cost."""
        return await call_external_api(
            "/api/v1/calculate/all-purpose-classic",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_all_purpose_serverless(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate All-Purpose serverless cost."""
        return await call_external_api(
            "/api/v1/calculate/all-purpose-serverless",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_dbsql_classic_pro(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate DBSQL classic/pro cost."""
        return await call_external_api(
            "/api/v1/calculate/dbsql-classic-pro",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_dbsql_serverless(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate DBSQL serverless cost."""
        return await call_external_api(
            "/api/v1/calculate/dbsql-serverless",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_dlt_classic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate DLT classic cost."""
        return await call_external_api(
            "/api/v1/calculate/dlt-classic",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_dlt_serverless(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate DLT serverless cost."""
        return await call_external_api(
            "/api/v1/calculate/dlt-serverless",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_model_serving(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Model Serving cost."""
        return await call_external_api(
            "/api/v1/calculate/model-serving",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_fmapi_databricks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate FMAPI Databricks cost."""
        return await call_external_api(
            "/api/v1/calculate/fmapi-databricks",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_fmapi_proprietary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate FMAPI Proprietary cost."""
        return await call_external_api(
            "/api/v1/calculate/fmapi-proprietary",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_vector_search(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Vector Search cost."""
        return await call_external_api(
            "/api/v1/calculate/vector-search",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def calculate_lakebase(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Lakebase cost."""
        return await call_external_api(
            "/api/v1/calculate/lakebase",
            method="POST",
            json_body=data,
            user_token=self.user_token
        )
    
    async def get_dbu_rates(
        self,
        cloud: str,
        region: str,
        tier: str
    ) -> Dict[str, Any]:
        """Get DBU rates for a cloud/region/tier combination.
        
        Returns available product types and their DBU prices.
        Used to determine which workload types are available in a region.
        """
        return await call_external_api(
            "/api/v1/pricing/dbu-rates",
            params={
                "cloud": cloud.upper(),
                "region": region,
                "tier": tier.upper()
            },
            user_token=self.user_token
        )

