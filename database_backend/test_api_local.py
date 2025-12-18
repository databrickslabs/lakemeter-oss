#!/usr/bin/env python3
"""
Test the Lakemeter API locally (outside Databricks notebook)
Reference: https://apps-cookbook.dev/docs/fastapi/getting_started/connections/connect_from_local
"""

import requests
import json
import sys

# API URL
API_BASE_URL = "https://lakemeter-api-335310294452632.aws.databricksapps.com"

def get_databricks_oauth_token():
    """
    Get OAuth token for Databricks Apps
    Reference: https://apps-cookbook.dev/docs/fastapi/getting_started/connections/connect_from_local
    
    Setup (one-time):
      databricks auth login --host <workspace-url> --profile lakemeter-oauth
    """
    import os
    
    # Method 1: Use Databricks SDK Config to get OAuth token (RECOMMENDED)
    try:
        from databricks.sdk.core import Config
        
        # Use the OAuth profile
        config = Config(profile="lakemeter-oauth")
        token = config.oauth_token().access_token
        print("   ✅ Using OAuth token from Databricks SDK (profile: lakemeter-oauth)")
        return token
    except ImportError:
        print("   ⚠️  databricks-sdk not installed")
        print("   💡 Install: pip install databricks-sdk")
        return None
    except Exception as e:
        print(f"   ⚠️  Error getting OAuth token: {e}")
        print("\n   💡 To fix:")
        print("      1. Run: databricks auth login --host https://fe-vm-lakemeter.cloud.databricks.com --profile lakemeter-oauth")
        print("      2. This will open your browser for OAuth authentication")
        print("      3. After login, re-run this script")
        return None
    
def test_endpoint(endpoint, method="GET", data=None, token=None):
    """Test an API endpoint"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, json=data, headers=headers)
        
        print(f"\n{'='*80}")
        print(f"TEST: {method} {endpoint}")
        print(f"{'='*80}")
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        # Try to parse as JSON
        try:
            json_response = response.json()
            print(f"\n✅ Response (JSON):")
            print(json.dumps(json_response, indent=2)[:500])  # Limit output
            if len(json.dumps(json_response)) > 500:
                print("... (truncated)")
            return json_response
        except:
            # Not JSON, show raw content
            content = response.text[:500]
            if "<html" in content.lower() or "<!doctype" in content.lower():
                print(f"\n❌ Response is HTML (authentication failed):")
                print(content[:200] + "...")
            else:
                print(f"\n❌ Response (not JSON):")
                print(content)
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("="*80)
    print("TESTING LAKEMETER API LOCALLY")
    print("="*80)
    print("\n📚 Reference: https://apps-cookbook.dev/docs/fastapi/getting_started/connections/connect_from_local")
    
    # Get OAuth token
    print("\n🔑 Getting OAuth token...")
    token = get_databricks_oauth_token()
    
    if not token:
        print("\n❌ Could not get OAuth token")
        sys.exit(1)
    
    print(f"✅ Token obtained: {token[:30]}...")
    
    # Test 1: Health check
    test_endpoint("/health", token=token)
    
    # Test 2: Get regions (data endpoint)
    test_endpoint("/api/v1/regions?cloud=AWS", token=token)
    
    # Test 3: Calculate JOBS Classic cost
    print("\n" + "="*80)
    print("TEST: POST /api/v1/calculate/jobs-classic")
    print("Testing with sample workload data...")
    print("="*80)
    
    test_data = {
        "cloud": "AWS",
        "region": "us-east-1",
        "tier": "PREMIUM",
        "driver_node_type": "m5.xlarge",
        "worker_node_type": "m5.xlarge",
        "num_workers": 10,
        "photon_enabled": False,
        "driver_pricing_tier": "on_demand",
        "worker_pricing_tier": "on_demand",
        "driver_payment_option": "NA",
        "worker_payment_option": "NA",
        "runs_per_day": 8,
        "avg_runtime_minutes": 60,
        "days_per_month": 30
    }
    
    result = test_endpoint("/api/v1/calculate/jobs-classic", method="POST", data=test_data, token=token)
    
    if result and result.get("success"):
        cost_data = result["data"]
        print(f"\n" + "="*80)
        print("💰 CALCULATION RESULTS")
        print("="*80)
        print(f"DBU Cost:     ${cost_data['dbu_costs']['dbu_cost_per_month']:.2f}/month")
        print(f"VM Cost:      ${cost_data['vm_costs']['vm_cost_per_month']:.2f}/month")
        print(f"Total Cost:   ${cost_data['total_cost']['cost_per_month']:.2f}/month")
        print(f"DBU per hour: {cost_data['dbu_costs']['dbu_per_hour']:.2f}")
        print(f"Hours/month:  {cost_data['usage']['hours_per_month']:.2f}")
    else:
        print("\n❌ Calculation failed")
    
    print("\n" + "="*80)
    print("✅ TESTS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
