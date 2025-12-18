# Databricks notebook source
# MAGIC %md
# MAGIC # API Testing Configuration
# MAGIC
# MAGIC **Purpose:** Configuration for testing the Lakemeter API endpoints
# MAGIC
# MAGIC **API Base URL:** Get this from your Databricks Apps deployment

# COMMAND ----------

# MAGIC %md
# MAGIC ## Get API URL
# MAGIC
# MAGIC Run this to get your API URL:

# COMMAND ----------

# MAGIC %sh
# MAGIC databricks apps list --profile lakemeter | grep lakemeter-api

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC
# MAGIC **Update this with your actual API URL:**

# COMMAND ----------

# Your API base URL (from Databricks Apps)
# Example: "https://your-workspace.cloud.databricks.com/apps/your-app-id"
API_BASE_URL = "https://lakemeter-api-335310294452632.aws.databricksapps.com"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

import requests
import json
from typing import Dict, Any, Optional

def get_auth_headers() -> Dict[str, str]:
    """
    Get authentication headers for API requests.
    Uses Databricks notebook context to get OAuth token.
    
    Returns:
        Dictionary with Authorization header
    """
    try:
        # Method 1: Try using dbutils directly (most common in Databricks notebooks)
        token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
        
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
    except Exception as e:
        pass  # Try next method
    
    try:
        # Method 2: Try importing from databricks.sdk.runtime
        from databricks.sdk.runtime import dbutils as sdk_dbutils
        token = sdk_dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
        
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
    except Exception as e:
        pass  # Try next method
    
    # If all methods fail
    print("⚠️  WARNING: Could not retrieve OAuth token!")
    print("    Make sure you're running this in a Databricks notebook")
    print("    API calls will fail with 401 Unauthorized")
    return {"Content-Type": "application/json"}


def api_get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Make a GET request to the API
    
    Args:
        endpoint: API endpoint (e.g., "/api/v1/regions")
        params: Optional query parameters
    
    Returns:
        JSON response as dictionary
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_auth_headers()
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


def api_post(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Make a POST request to the API
    
    Args:
        endpoint: API endpoint (e.g., "/api/v1/calculate/jobs-classic")
        data: Request body as dictionary
    
    Returns:
        JSON response as dictionary
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = get_auth_headers()
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()


def print_response(response: Dict[str, Any], title: str = "API Response"):
    """Pretty print API response"""
    print("=" * 100)
    print(title)
    print("=" * 100)
    print(json.dumps(response, indent=2))
    print("=" * 100)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Connection

# COMMAND ----------

print("🔍 Testing API Connection...")
print(f"   API URL: {API_BASE_URL}")
print()

try:
    # Try to get regions as a simple test (requires auth)
    response = api_get("/api/v1/regions", {"cloud": "AWS"})
    
    if response.get("success"):
        print("✅ API Connection Successful!")
        print(f"   Authenticated: Yes (using Databricks OAuth)")
        print(f"   Sample data: Found {response['data']['count']} AWS regions")
    else:
        print("⚠️  API responded but returned an error:")
        print(f"   {response}")
except Exception as e:
    print(f"❌ API Connection Failed: {e}")
    print()
    print("💡 Troubleshooting:")
    print("   1. Make sure API_BASE_URL is correct (check above)")
    print("   2. Make sure you're running this in a Databricks notebook")
    print("   3. OAuth token is retrieved automatically from notebook context")
    print()
    print("🔧 To fix:")
    print("   - Verify API is deployed: databricks apps list --profile lakemeter")
    print("   - Check API URL matches the deployed app URL")

# COMMAND ----------

print("=" * 100)
print("✅ API Configuration Loaded!")
print("=" * 100)
print(f"   API URL: {API_BASE_URL}")

# Check if we can get auth token
headers = get_auth_headers()
if "Authorization" in headers:
    token_preview = headers["Authorization"][:30] + "..." if len(headers["Authorization"]) > 30 else headers["Authorization"]
    print(f"   Auth Token: {token_preview}")
    print(f"   Status: ✅ OAuth token retrieved successfully")
else:
    print(f"   Auth Token: ❌ Not found")
    print(f"   Status: ⚠️  API calls will fail")

print()
print("📝 To use in other notebooks:")
print("   %run ./00_API_Config")
print("=" * 100)

