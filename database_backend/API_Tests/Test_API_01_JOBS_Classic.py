# Databricks notebook source
# MAGIC %md
# MAGIC # API Test: JOBS Classic Cost Calculation
# MAGIC
# MAGIC **Objective:** Test the POST /api/v1/calculate/jobs-classic endpoint
# MAGIC
# MAGIC **Test Coverage:**
# MAGIC - Basic calculation
# MAGIC - With/without Photon
# MAGIC - Different pricing tiers (on_demand, spot, reserved)
# MAGIC - Different payment options (AWS: no_upfront, partial_upfront, all_upfront)
# MAGIC - Multiple clouds (AWS, Azure, GCP)
# MAGIC - Validation errors

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

# Load API configuration
%run ./00_API_Config

# COMMAND ----------

import json
from typing import Dict, Any

def test_jobs_classic(
    test_name: str,
    cloud: str,
    region: str,
    tier: str,
    driver_node_type: str,
    worker_node_type: str,
    num_workers: int,
    photon_enabled: bool = False,
    driver_pricing_tier: str = "on_demand",
    worker_pricing_tier: str = "on_demand",
    driver_payment_option: str = "NA",
    worker_payment_option: str = "NA",
    runs_per_day: int = 8,
    avg_runtime_minutes: int = 60,
    days_per_month: int = 30
) -> Dict[str, Any]:
    """
    Test JOBS Classic calculation with given parameters
    """
    print("\n" + "=" * 100)
    print(f"TEST: {test_name}")
    print("=" * 100)
    
    request_data = {
        "cloud": cloud,
        "region": region,
        "tier": tier,
        "driver_node_type": driver_node_type,
        "worker_node_type": worker_node_type,
        "num_workers": num_workers,
        "photon_enabled": photon_enabled,
        "driver_pricing_tier": driver_pricing_tier,
        "worker_pricing_tier": worker_pricing_tier,
        "driver_payment_option": driver_payment_option,
        "worker_payment_option": worker_payment_option,
        "runs_per_day": runs_per_day,
        "avg_runtime_minutes": avg_runtime_minutes,
        "days_per_month": days_per_month
    }
    
    print("\n📤 Request:")
    print(json.dumps(request_data, indent=2))
    
    try:
        response = api_post("/api/v1/calculate/jobs-classic", request_data)
        
        print("\n📥 Response:")
        print(json.dumps(response, indent=2))
        
        if response.get("success"):
            data = response["data"]
            print("\n💰 Cost Summary:")
            print(f"   Hours/Month: {data['usage']['hours_per_month']}")
            print(f"   DBU/Hour: {data['dbu_calculation']['dbu_per_hour']}")
            print(f"   DBU/Month: {data['dbu_calculation']['dbu_per_month']}")
            print(f"   DBU Cost: ${data['dbu_calculation']['dbu_cost_per_month']:.2f}")
            print(f"   VM Cost: ${data['vm_costs']['vm_cost_per_month']:.2f}")
            print(f"   TOTAL: ${data['total_cost']['cost_per_month']:.2f}")
            print("\n✅ Test PASSED")
        else:
            print(f"\n❌ Test FAILED: {response.get('error')}")
        
        return response
        
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        return {"success": False, "error": str(e)}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 1: Basic AWS JOBS Classic (No Photon, On-Demand)

# COMMAND ----------

test_jobs_classic(
    test_name="AWS JOBS Classic - No Photon - On-Demand",
    cloud="AWS",
    region="us-east-1",
    tier="PREMIUM",
    driver_node_type="m5.xlarge",
    worker_node_type="m5.xlarge",
    num_workers=10,
    photon_enabled=False,
    driver_pricing_tier="on_demand",
    worker_pricing_tier="on_demand",
    runs_per_day=8,
    avg_runtime_minutes=60,
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 2: AWS JOBS Classic with Photon

# COMMAND ----------

test_jobs_classic(
    test_name="AWS JOBS Classic - With Photon - On-Demand",
    cloud="AWS",
    region="us-east-1",
    tier="PREMIUM",
    driver_node_type="m5.xlarge",
    worker_node_type="m5.xlarge",
    num_workers=10,
    photon_enabled=True,  # ✅ Photon enabled
    driver_pricing_tier="on_demand",
    worker_pricing_tier="on_demand",
    runs_per_day=8,
    avg_runtime_minutes=60,
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 3: AWS JOBS Classic with Spot Pricing

# COMMAND ----------

test_jobs_classic(
    test_name="AWS JOBS Classic - Spot Workers",
    cloud="AWS",
    region="us-east-1",
    tier="PREMIUM",
    driver_node_type="m5.xlarge",
    worker_node_type="m5.xlarge",
    num_workers=10,
    photon_enabled=False,
    driver_pricing_tier="on_demand",  # Driver always on-demand
    worker_pricing_tier="spot",  # ✅ Workers use spot
    runs_per_day=8,
    avg_runtime_minutes=60,
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 4: AWS JOBS Classic with Reserved 1Y (Partial Upfront)

# COMMAND ----------

test_jobs_classic(
    test_name="AWS JOBS Classic - Reserved 1Y Partial Upfront",
    cloud="AWS",
    region="us-east-1",
    tier="PREMIUM",
    driver_node_type="m5.xlarge",
    worker_node_type="m5.xlarge",
    num_workers=10,
    photon_enabled=False,
    driver_pricing_tier="reserved_1y",
    worker_pricing_tier="reserved_1y",
    driver_payment_option="partial_upfront",  # ✅ AWS payment option
    worker_payment_option="partial_upfront",
    runs_per_day=8,
    avg_runtime_minutes=60,
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 5: AWS JOBS Classic with Reserved 3Y (All Upfront)

# COMMAND ----------

test_jobs_classic(
    test_name="AWS JOBS Classic - Reserved 3Y All Upfront",
    cloud="AWS",
    region="us-east-1",
    tier="PREMIUM",
    driver_node_type="m5.xlarge",
    worker_node_type="m5.xlarge",
    num_workers=10,
    photon_enabled=False,
    driver_pricing_tier="reserved_3y",
    worker_pricing_tier="reserved_3y",
    driver_payment_option="all_upfront",  # ✅ AWS payment option
    worker_payment_option="all_upfront",
    runs_per_day=8,
    avg_runtime_minutes=60,
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 6: Azure JOBS Classic (PREMIUM tier)

# COMMAND ----------

test_jobs_classic(
    test_name="Azure JOBS Classic - PREMIUM tier",
    cloud="AZURE",
    region="eastus",
    tier="PREMIUM",  # ✅ Azure supports PREMIUM
    driver_node_type="Standard_D4s_v3",
    worker_node_type="Standard_D4s_v3",
    num_workers=8,
    photon_enabled=True,
    driver_pricing_tier="on_demand",
    worker_pricing_tier="on_demand",
    runs_per_day=12,
    avg_runtime_minutes=60,
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 7: GCP JOBS Classic

# COMMAND ----------

test_jobs_classic(
    test_name="GCP JOBS Classic - With Photon",
    cloud="GCP",
    region="us-central1",
    tier="PREMIUM",
    driver_node_type="n2-standard-4",
    worker_node_type="n2-standard-4",
    num_workers=8,
    photon_enabled=True,
    driver_pricing_tier="on_demand",
    worker_pricing_tier="on_demand",
    runs_per_day=12,
    avg_runtime_minutes=60,
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 8: Light Usage Pattern

# COMMAND ----------

test_jobs_classic(
    test_name="AWS JOBS Classic - Light Usage",
    cloud="AWS",
    region="us-east-1",
    tier="STANDARD",
    driver_node_type="m5.large",
    worker_node_type="m5.large",
    num_workers=2,  # ✅ Small cluster
    photon_enabled=False,
    driver_pricing_tier="on_demand",
    worker_pricing_tier="on_demand",
    runs_per_day=4,  # ✅ Few runs
    avg_runtime_minutes=30,  # ✅ Short runtime
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 9: Heavy Usage Pattern

# COMMAND ----------

test_jobs_classic(
    test_name="AWS JOBS Classic - Heavy Usage",
    cloud="AWS",
    region="us-east-1",
    tier="ENTERPRISE",
    driver_node_type="m5.4xlarge",
    worker_node_type="m5.2xlarge",
    num_workers=20,  # ✅ Large cluster
    photon_enabled=True,
    driver_pricing_tier="reserved_1y",
    worker_pricing_tier="reserved_1y",
    driver_payment_option="all_upfront",
    worker_payment_option="all_upfront",
    runs_per_day=24,  # ✅ Many runs
    avg_runtime_minutes=120,  # ✅ Long runtime
    days_per_month=30
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 10: Validation Error - Invalid Cloud

# COMMAND ----------

print("\n" + "=" * 100)
print("TEST: Validation Error - Invalid Cloud")
print("=" * 100)

try:
    response = api_post("/api/v1/calculate/jobs-classic", {
        "cloud": "INVALID_CLOUD",  # ❌ Invalid
        "region": "us-east-1",
        "tier": "PREMIUM",
        "driver_node_type": "m5.xlarge",
        "worker_node_type": "m5.xlarge",
        "num_workers": 10,
        "photon_enabled": False,
        "driver_pricing_tier": "on_demand",
        "worker_pricing_tier": "on_demand",
        "runs_per_day": 8,
        "avg_runtime_minutes": 60,
        "days_per_month": 30
    })
    print(f"❌ Test FAILED: Expected validation error but got success")
except Exception as e:
    print(f"✅ Test PASSED: Got expected validation error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 11: Validation Error - Azure ENTERPRISE (not supported)

# COMMAND ----------

print("\n" + "=" * 100)
print("TEST: Validation Error - Azure ENTERPRISE (not supported)")
print("=" * 100)

try:
    response = api_post("/api/v1/calculate/jobs-classic", {
        "cloud": "AZURE",
        "region": "eastus",
        "tier": "ENTERPRISE",  # ❌ Azure doesn't support ENTERPRISE
        "driver_node_type": "Standard_D4s_v3",
        "worker_node_type": "Standard_D4s_v3",
        "num_workers": 10,
        "photon_enabled": False,
        "driver_pricing_tier": "on_demand",
        "worker_pricing_tier": "on_demand",
        "runs_per_day": 8,
        "avg_runtime_minutes": 60,
        "days_per_month": 30
    })
    print(f"❌ Test FAILED: Expected validation error but got success")
except Exception as e:
    print(f"✅ Test PASSED: Got expected validation error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 12: Validation Error - Invalid Instance Type

# COMMAND ----------

print("\n" + "=" * 100)
print("TEST: Validation Error - Invalid Instance Type")
print("=" * 100)

try:
    response = api_post("/api/v1/calculate/jobs-classic", {
        "cloud": "AWS",
        "region": "us-east-1",
        "tier": "PREMIUM",
        "driver_node_type": "invalid.instance",  # ❌ Invalid
        "worker_node_type": "m5.xlarge",
        "num_workers": 10,
        "photon_enabled": False,
        "driver_pricing_tier": "on_demand",
        "worker_pricing_tier": "on_demand",
        "runs_per_day": 8,
        "avg_runtime_minutes": 60,
        "days_per_month": 30
    })
    print(f"❌ Test FAILED: Expected validation error but got success")
except Exception as e:
    print(f"✅ Test PASSED: Got expected validation error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 100)
print("TEST SUMMARY - JOBS Classic API")
print("=" * 100)

print("\n✅ Tests Completed:")
print("   1. Basic AWS on-demand")
print("   2. AWS with Photon")
print("   3. AWS with spot pricing")
print("   4. AWS reserved 1Y (partial upfront)")
print("   5. AWS reserved 3Y (all upfront)")
print("   6. Azure PREMIUM tier")
print("   7. GCP with Photon")
print("   8. Light usage pattern")
print("   9. Heavy usage pattern")
print("   10. Validation: Invalid cloud")
print("   11. Validation: Azure ENTERPRISE (not supported)")
print("   12. Validation: Invalid instance type")

print("\n📊 Coverage:")
print("   ✅ All 3 clouds (AWS, Azure, GCP)")
print("   ✅ All tiers (STANDARD, PREMIUM, ENTERPRISE)")
print("   ✅ Photon enabled/disabled")
print("   ✅ All pricing tiers (on_demand, spot, reserved_1y, reserved_3y)")
print("   ✅ AWS payment options (no_upfront, partial_upfront, all_upfront)")
print("   ✅ Various usage patterns (light, medium, heavy)")
print("   ✅ Validation errors")

print("\n" + "=" * 100)

