# Quick Test Examples

Test your API directly in the Swagger UI or using curl.

## Swagger UI (Requires Authentication)

**Open in browser:**
```
https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
```

**🔐 Authentication:**
The API requires OAuth authentication. When testing in Swagger UI:
1. You'll need to be logged into Databricks in the same browser
2. Or click the "Authorize" button and provide a Databricks token

**Steps:**
Navigate to: **Cost Calculation → POST /api/v1/calculate/jobs-classic**

Click **"Try it out"** and paste one of the examples below.

---

## Example 1: Basic AWS JOBS Classic (No Photon)

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "photon_enabled": false,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "on_demand",
  "driver_payment_option": "NA",
  "worker_payment_option": "NA",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
}
```

**Expected Result:**
- Hours/Month: ~240
- DBU Cost: Based on PREMIUM tier pricing
- VM Cost: On-demand pricing for 1 driver + 10 workers
- Total Cost: DBU + VM costs

---

## Example 2: AWS with Photon + Spot Workers

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "photon_enabled": true,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "spot",
  "driver_payment_option": "NA",
  "worker_payment_option": "NA",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
}
```

**Expected Result:**
- DBU/hour will be ~2x higher (Photon multiplier)
- VM cost will be lower (spot pricing on workers)
- Total cost depends on DBU vs VM cost ratio

---

## Example 3: AWS Reserved 1Y (Partial Upfront)

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "photon_enabled": false,
  "driver_pricing_tier": "reserved_1y",
  "worker_pricing_tier": "reserved_1y",
  "driver_payment_option": "partial_upfront",
  "worker_payment_option": "partial_upfront",
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
}
```

**Expected Result:**
- Lower VM costs (reserved pricing)
- Same DBU costs
- Better for long-running production workloads

---

## Example 4: Azure PREMIUM (Simple)

```json
{
  "cloud": "AZURE",
  "region": "eastus",
  "tier": "PREMIUM",
  "driver_node_type": "Standard_D4s_v3",
  "worker_node_type": "Standard_D4s_v3",
  "num_workers": 8,
  "photon_enabled": true,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "on_demand",
  "driver_payment_option": "NA",
  "worker_payment_option": "NA",
  "runs_per_day": 12,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
}
```

**Note:** Azure does not support ENTERPRISE tier or AWS-style payment options.

---

## Example 5: Light Usage

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "STANDARD",
  "driver_node_type": "m5.large",
  "worker_node_type": "m5.large",
  "num_workers": 2,
  "photon_enabled": false,
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "on_demand",
  "driver_payment_option": "NA",
  "worker_payment_option": "NA",
  "runs_per_day": 4,
  "avg_runtime_minutes": 30,
  "days_per_month": 30
}
```

**Expected Result:**
- Low hours/month: 60 hours (4 runs × 0.5 hours × 30 days)
- Smaller instances (m5.large)
- Fewer workers (2)
- Lower total cost

---

## Example 6: Heavy Usage

```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "ENTERPRISE",
  "driver_node_type": "m5.4xlarge",
  "worker_node_type": "m5.2xlarge",
  "num_workers": 20,
  "photon_enabled": true,
  "driver_pricing_tier": "reserved_1y",
  "worker_pricing_tier": "reserved_1y",
  "driver_payment_option": "all_upfront",
  "worker_payment_option": "all_upfront",
  "runs_per_day": 24,
  "avg_runtime_minutes": 120,
  "days_per_month": 30
}
```

**Expected Result:**
- High hours/month: 1440 hours (24 runs × 2 hours × 30 days)
- Large instances (m5.4xlarge, m5.2xlarge)
- Many workers (20)
- Reserved pricing for cost savings
- High total cost

---

## Using curl (Requires Authentication)

**🔐 Get a Databricks Token:**
```bash
# Option 1: From Databricks workspace
# User Settings → Developer → Access Tokens → Generate New Token

# Option 2: From CLI (if configured)
databricks auth token --profile lakemeter
```

**With authentication:**
```bash
# Set your token
export DATABRICKS_TOKEN="dapi123abc..."

# Basic test
curl -X POST "https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/calculate/jobs-classic" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "driver_node_type": "m5.xlarge",
    "worker_node_type": "m5.xlarge",
    "num_workers": 10,
    "photon_enabled": false,
    "driver_pricing_tier": "on_demand",
    "worker_pricing_tier": "on_demand",
    "driver_payment_option": "NA",
    "worker_payment_option": "NA",
    "runs_per_day": 8,
    "avg_runtime_minutes": 60,
    "days_per_month": 30
  }'
```

**⚠️ Note:** Databricks notebooks automatically handle authentication. Use curl only if testing outside of Databricks.

---

## Understanding the Response

The API returns a detailed breakdown:

```json
{
  "success": true,
  "data": {
    "workload_type": "JOBS_CLASSIC",
    "configuration": {
      "cloud": "AWS",
      "region": "us-east-1",
      "tier": "PREMIUM",
      "driver_node_type": "m5.xlarge",
      "worker_node_type": "m5.xlarge",
      "num_workers": 10,
      "photon_enabled": false,
      ...
    },
    "usage": {
      "runs_per_day": 8,
      "avg_runtime_minutes": 60,
      "days_per_month": 30,
      "hours_per_month": 240.0
    },
    "dbu_calculation": {
      "dbu_per_hour": 12.5,        // DBU rate per hour
      "dbu_per_month": 3000.0,     // Total DBUs for the month
      "dbu_price": 0.15,           // Price per DBU
      "dbu_cost_per_month": 450.0  // DBU cost (3000 × 0.15)
    },
    "vm_costs": {
      "driver_vm_cost_per_hour": 0.192,
      "worker_vm_cost_per_hour": 0.096,
      "total_vm_cost_per_hour": 1.152,
      "driver_vm_cost_per_month": 46.08,
      "total_worker_vm_cost_per_month": 230.40,
      "vm_cost_per_month": 276.48
    },
    "total_cost": {
      "cost_per_month": 726.48,     // Total: DBU + VM
      "breakdown": {
        "dbu_cost": 450.0,
        "vm_cost": 276.48
      }
    }
  }
}
```

### Key Fields:
- **hours_per_month**: Calculated from runs × runtime × days
- **dbu_per_hour**: Instance DBU rates × photon multiplier
- **dbu_cost_per_month**: Total DBU cost based on tier pricing
- **vm_cost_per_month**: Infrastructure costs (driver + workers)
- **cost_per_month**: Total monthly cost (DBU + VM)

---

## Common Errors

### Invalid Cloud
```json
{
  "cloud": "INVALID"
  ...
}
```
**Error:** 400 Bad Request - Invalid cloud 'INVALID'. Must be one of: AWS, AZURE, GCP

### Azure ENTERPRISE (Not Supported)
```json
{
  "cloud": "AZURE",
  "tier": "ENTERPRISE"
  ...
}
```
**Error:** 400 Bad Request - Azure does not support ENTERPRISE tier

### Invalid Instance Type
```json
{
  "driver_node_type": "invalid.instance"
  ...
}
```
**Error:** 400 Bad Request - Invalid instance type

---

## Tips

1. **Start simple** - Test Example 1 first to verify everything works
2. **Compare costs** - Run with/without Photon to see the impact
3. **Test pricing tiers** - Compare on_demand vs spot vs reserved
4. **Try different clouds** - AWS, Azure, GCP have different pricing
5. **Validate errors** - Try invalid inputs to test validation

---

## Next Steps

Once you've tested JOBS Classic:
1. Test JOBS Serverless (coming soon)
2. Test DBSQL (Classic, Pro, Serverless)
3. Test other workload types

