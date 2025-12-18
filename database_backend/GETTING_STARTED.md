# 🚀 Getting Started with Lakemeter API

**Welcome to the Lakemeter API Beta!**

This guide will have you making your first API call in less than 5 minutes.

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Get Your OAuth Token (1 minute)

**Option A: From Databricks Notebook**
```python
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
print(f"Your token: {token}")
```

**Option B: From Local Terminal (if CLI configured)**
```bash
databricks auth token --host https://your-workspace.cloud.databricks.com
```

Copy the token value. You'll need it for authentication.

---

### Step 2: Test the API (1 minute)

**Health Check (No Auth Required):**
```bash
curl https://lakemeter-api-335310294452632.aws.databricksapps.com/health
```

**Expected Response:**
```json
{"status": "healthy", "timestamp": "2024-12-18T10:00:00Z"}
```

**Get Available Clouds (Auth Required):**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/clouds
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "count": 3,
    "clouds": ["AWS", "AZURE", "GCP"]
  }
}
```

✅ **If you see this, you're authenticated and ready to go!**

---

### Step 3: Calculate Your First Cost (3 minutes)

Let's calculate the cost of a simple JOBS cluster:

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
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
    "hours_per_month": 160
  }' \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/calculate/jobs-classic
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "workload_type": "JOBS_CLASSIC",
    "usage": {
      "hours_per_month": 160.0
    },
    "dbu_costs": {
      "dbu_per_hour": 10.5,
      "dbu_cost_per_month": 176.4
    },
    "vm_costs": {
      "driver_vm_cost_per_hour": 0.192,
      "worker_vm_cost_per_hour": 0.384,
      "total_vm_cost_per_hour": 4.032,
      "vm_cost_per_month": 645.12
    },
    "total_cost": {
      "cost_per_month": 821.52
    }
  }
}
```

🎉 **Congratulations! You just calculated your first Databricks workload cost!**

---

## 📚 Next Steps

### Explore the API

1. **Browse Interactive Docs**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
2. **Read Full API Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
3. **Try More Endpoints**: See examples below

### Try Different Workload Types

**DBSQL Serverless:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "warehouse_size": "Medium",
    "num_clusters": 1,
    "hours_per_month": 730
  }' \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/calculate/dbsql-serverless
```

**Model Serving:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "gpu_type": "gpu_small_t4",
    "hours_per_month": 730
  }' \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/calculate/model-serving
```

**FMAPI (AI Models):**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "provider": "anthropic",
    "model": "claude-sonnet-4-5",
    "endpoint_type": "global",
    "context_length": "all",
    "rate_type": "input_token",
    "quantity": 1000000
  }' \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/calculate/fmapi-proprietary
```

---

## 🛠️ Tools & Tips

### Using Postman

1. **Create a new Collection**: "Lakemeter API"
2. **Set Base URL**: `https://lakemeter-api-335310294452632.aws.databricksapps.com`
3. **Add Authorization Header**:
   - Key: `Authorization`
   - Value: `Bearer YOUR_TOKEN`
4. **Import OpenAPI Spec**: File → Import → `https://lakemeter-api-335310294452632.aws.databricksapps.com/openapi.json`

### Using Python

```python
import requests

API_BASE = "https://lakemeter-api-335310294452632.aws.databricksapps.com"
TOKEN = "your_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Get available clouds
response = requests.get(f"{API_BASE}/api/v1/clouds", headers=headers)
print(response.json())

# Calculate cost
request_data = {
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "driver_node_type": "m5.xlarge",
    "worker_node_type": "m5.xlarge",
    "num_workers": 10,
    "photon_enabled": True,
    "driver_pricing_tier": "on_demand",
    "worker_pricing_tier": "spot",
    "driver_payment_option": "NA",
    "worker_payment_option": "NA",
    "hours_per_month": 160
}

response = requests.post(
    f"{API_BASE}/api/v1/calculate/jobs-classic",
    json=request_data,
    headers=headers
)
print(response.json())
```

### Using JavaScript/TypeScript

```typescript
const API_BASE = "https://lakemeter-api-335310294452632.aws.databricksapps.com";
const TOKEN = "your_token_here";

const headers = {
  "Authorization": `Bearer ${TOKEN}`,
  "Content-Type": "application/json"
};

// Get available clouds
const cloudsResponse = await fetch(`${API_BASE}/api/v1/clouds`, { headers });
const clouds = await cloudsResponse.json();
console.log(clouds);

// Calculate cost
const requestData = {
  cloud: "AWS",
  region: "us-east-1",
  tier: "PREMIUM",
  driver_node_type: "m5.xlarge",
  worker_node_type: "m5.xlarge",
  num_workers: 10,
  photon_enabled: true,
  driver_pricing_tier: "on_demand",
  worker_pricing_tier: "spot",
  driver_payment_option: "NA",
  worker_payment_option: "NA",
  hours_per_month: 160
};

const costResponse = await fetch(
  `${API_BASE}/api/v1/calculate/jobs-classic`,
  {
    method: "POST",
    headers,
    body: JSON.stringify(requestData)
  }
);
const cost = await costResponse.json();
console.log(cost);
```

---

## 🎯 Common Use Cases

### Use Case 1: Build a Cost Calculator UI

**Flow:**
1. Load dropdown options (clouds, regions, instance types)
2. User selects configuration
3. Validate selections as user types
4. Calculate cost on form submit
5. Display breakdown (DBU + VM costs)

**Key Endpoints:**
- `GET /api/v1/clouds`
- `GET /api/v1/regions?cloud=AWS`
- `GET /api/v1/instances/types?cloud=AWS&region=us-east-1`
- `POST /api/v1/calculate/jobs-classic`

---

### Use Case 2: Compare Pricing Across Clouds

**Flow:**
1. Define workload configuration
2. Calculate cost for AWS
3. Calculate cost for Azure
4. Calculate cost for GCP
5. Compare and display results

**Example:**
```python
clouds = ["AWS", "AZURE", "GCP"]
regions = {
    "AWS": "us-east-1",
    "AZURE": "eastus",
    "GCP": "us-central1"
}

for cloud in clouds:
    request_data["cloud"] = cloud
    request_data["region"] = regions[cloud]
    response = requests.post(url, json=request_data, headers=headers)
    result = response.json()
    print(f"{cloud}: ${result['data']['total_cost']['cost_per_month']:.2f}/month")
```

---

### Use Case 3: Optimize Instance Selection

**Flow:**
1. Get available instance types for cloud/region
2. Filter by vCPU/memory requirements
3. Calculate cost for each option
4. Sort by total cost
5. Present recommendations

**Key Endpoints:**
- `GET /api/v1/instances/types?cloud=AWS&region=us-east-1&min_vcpus=8&max_vcpus=16`
- `POST /api/v1/calculate/jobs-classic` (iterate for each instance type)

---

### Use Case 4: Budget Estimation

**Flow:**
1. User inputs usage patterns (runs per day, runtime)
2. API calculates hours per month automatically
3. Display cost breakdown
4. Allow adjustments and recalculation

**Example Request (Run-Based):**
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

**API calculates**: `hours_per_month = (8 runs × 60 min × 30 days) / 60 = 240 hours`

---

## 🐛 Troubleshooting

### Problem: 401 Unauthorized

**Cause**: Invalid or expired OAuth token

**Solution:**
1. Generate a fresh token (see Step 1)
2. Ensure token is in `Authorization: Bearer TOKEN` header
3. Check token hasn't expired (tokens expire after 1 hour by default)

---

### Problem: Invalid Instance Type

**Cause**: Instance type not available for specified cloud/region

**Solution:**
1. Check error message for list of available instance types
2. Use `/api/v1/instances/types` to get valid options
3. Verify cloud and region are correct

**Example Error:**
```json
{
  "success": false,
  "detail": {
    "code": "INVALID_INSTANCE_TYPE",
    "message": "Instance type 'm5.xlarge' not found for AZURE.",
    "field": "instance_type",
    "allowed_values": ["Standard_D4s_v3", "Standard_E4s_v3", ...]
  }
}
```

---

### Problem: Payment Option Error

**Cause**: Using wrong payment option for cloud/pricing tier

**Solution:**
- **AWS on-demand/spot**: Use `"payment_option": "NA"`
- **AWS reserved**: Use `"no_upfront"`, `"partial_upfront"`, or `"all_upfront"`
- **Azure/GCP (all tiers)**: Always use `"payment_option": "NA"`

---

### Problem: $0 Cost Returned

**Possible causes:**
1. Invalid parameter combination
2. Missing required fields
3. Wrong pricing tier for workload type

**Solution:**
1. Check all required fields are provided
2. Verify pricing tier is valid for your cloud
3. Check error messages in response
4. Review [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)

---

### Problem: Slow Response Times

**Cause**: No caching, all requests hit database

**Solution:**
1. Cache reference data on frontend (clouds, regions, etc.)
2. Avoid making excessive requests
3. See [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) for caching recommendations

---

## 📖 Documentation Resources

### Essential Reading
- **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** - Complete API reference
- **[AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md)** - For AI agent integration
- **[BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)** - How to test and report issues
- **[KNOWN_ISSUES.md](./KNOWN_ISSUES.md)** - Current limitations and workarounds
- **[BETA_RELEASE_NOTES.md](./BETA_RELEASE_NOTES.md)** - What's in this release

### Interactive Tools
- **Swagger UI**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
- **OpenAPI Spec**: https://lakemeter-api-335310294452632.aws.databricksapps.com/openapi.json

### GitHub
- **Repository**: https://github.com/muharandy/promptsizer/tree/database_backend/database_backend
- **Report Issues**: https://github.com/muharandy/promptsizer/issues

---

## 🎓 Learning Path

### Beginner (Day 1)
1. ✅ Get your OAuth token
2. ✅ Make your first API call (health check)
3. ✅ Get reference data (clouds, regions)
4. ✅ Calculate a simple JOBS Classic cost
5. ✅ Review Swagger UI

### Intermediate (Day 2-3)
1. Calculate costs for different workload types (DBSQL, Model Serving)
2. Experiment with run-based vs direct hours
3. Test cloud-specific features (AWS payment options)
4. Handle errors gracefully
5. Build a simple cost calculator

### Advanced (Week 1)
1. Integrate with your frontend framework
2. Implement caching for reference data
3. Build comparison features (cloud vs cloud, on-demand vs reserved)
4. Optimize for performance (batch requests)
5. Contribute to beta testing (report issues, suggest improvements)

---

## 💡 Pro Tips

### 1. Cache Reference Data
```javascript
// Good: Cache rarely-changing data
const clouds = await fetchAndCache('/api/v1/clouds', '1h');
const regions = await fetchAndCache('/api/v1/regions?cloud=AWS', '1h');

// Bad: Re-fetch on every render
const clouds = await fetch('/api/v1/clouds'); // Every time!
```

### 2. Validate Before Calculating
```javascript
// Good: Validate inputs first
const instanceTypesResponse = await fetch('/api/v1/instances/types?cloud=AWS&region=us-east-1');
const validInstances = await instanceTypesResponse.json();
// Build dropdown from validInstances
// Then calculate with user's selection

// Bad: Try to calculate, handle error
const costResponse = await fetch('/api/v1/calculate/jobs-classic', {...});
// User sees error instead of valid options
```

### 3. Use Error Messages
```javascript
// Good: Show helpful error to user
if (!response.ok) {
  const error = await response.json();
  if (error.detail.allowed_values) {
    showDropdown(error.detail.allowed_values); // Let user pick valid option
  } else {
    showError(error.detail.message); // Show clear error message
  }
}

// Bad: Generic error
if (!response.ok) {
  showError("Something went wrong"); // Not helpful!
}
```

### 4. Handle Cloud Differences
```javascript
// Good: Conditional UI based on cloud
if (selectedCloud === 'AWS' && pricingTier.includes('reserved')) {
  showPaymentOptions(['no_upfront', 'partial_upfront', 'all_upfront']);
} else {
  hidePaymentOptions(); // Azure/GCP or non-reserved
}

// Bad: Always show all options
showPaymentOptions(['NA', 'no_upfront', 'partial_upfront', 'all_upfront']);
// User picks wrong option for their cloud → API error
```

---

## 🎉 You're Ready!

You now have everything you need to start using the Lakemeter API. 

**Next Steps:**
1. Make your first API call (if you haven't already)
2. Explore Swagger UI for more endpoints
3. Read the full API documentation
4. Start integrating with your application
5. Report any issues you find

**Need help?**
- Check [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for detailed endpoint info
- Review [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md) for support options
- Browse [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) for common problems
- Create an issue on GitHub for new problems

**Happy building! 🚀**

