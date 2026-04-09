# Databricks notebook source
# MAGIC %md
# MAGIC # Quick API Authentication Test
# MAGIC 
# MAGIC Test different authentication methods to see what the API accepts

# COMMAND ----------

import requests
import json

API_BASE_URL = "https://lakemeter-api-335310294452632.aws.databricksapps.com"

# Get your token
try:
    token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().getOrElse(None)
    print(f"Token obtained: {token[:15] if token else 'None'}...{token[-10:] if token else ''}")
except:
    token = None
    print("Could not get token automatically - please provide manually")

# COMMAND ----------

# Test 1: No authentication
print("=" * 80)
print("TEST 1: No Authentication")
print("=" * 80)

try:
    response = requests.get(f"{API_BASE_URL}/docs", timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# COMMAND ----------

# Test 2: Bearer token authentication
print("\n" + "=" * 80)
print("TEST 2: Bearer Token Authentication")
print("=" * 80)

if token:
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try GET docs
    try:
        response = requests.get(f"{API_BASE_URL}/docs", headers=headers, timeout=10)
        print(f"GET /docs - Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Try simple calculation
    try:
        test_payload = {
            "cloud": "AWS",
            "region": "us-east-1",
            "tier": "PREMIUM",
            "cu_per_node": 2,
            "storage_gb": 0,
            "hours_per_month": 730
        }
        response = requests.post(
            f"{API_BASE_URL}/api/v1/calculate/lakebase",
            json=test_payload,
            headers=headers,
            timeout=10
        )
        print(f"\nPOST /api/v1/calculate/lakebase - Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 401:
            print("\n❌ 401 Unauthorized")
            print("The API is rejecting the bearer token.")
            print("\nPossible causes:")
            print("1. Databricks App not configured to accept notebook authentication")
            print("2. App requires OAuth or service principal")
            print("3. App authentication settings need to be updated")
            
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No token available - skipping test")

# COMMAND ----------

# Test 3: Check if API is public or requires specific auth
print("\n" + "=" * 80)
print("TEST 3: API Info Endpoint")
print("=" * 80)

try:
    response = requests.get(f"{API_BASE_URL}/openapi.json", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        openapi = response.json()
        if "components" in openapi and "securitySchemes" in openapi["components"]:
            print("\nSecurity schemes defined in API:")
            print(json.dumps(openapi["components"]["securitySchemes"], indent=2))
        else:
            print("No security schemes defined (API might be public)")
except Exception as e:
    print(f"Error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC Based on the test results:
# MAGIC 
# MAGIC **If 401 errors persist:**
# MAGIC 1. Check Databricks App settings in the workspace
# MAGIC 2. The app may need to be configured to accept incoming requests
# MAGIC 3. May need to use OAuth or service principal authentication
# MAGIC 
# MAGIC **If API works without authentication:**
# MAGIC - Update backfill notebook to not require auth
# MAGIC 
# MAGIC **Contact the API owner** (check app configuration in Databricks workspace)
