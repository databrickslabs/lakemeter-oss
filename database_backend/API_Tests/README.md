# API Tests

Test suite for the Lakemeter Cost Calculation API endpoints.

## Setup

### 1. Get Your API URL

First, deploy your API and get the URL:

```bash
databricks apps list --profile lakemeter | grep lakemeter-api
```

You should see something like:
```
lakemeter-api  https://your-workspace.cloud.databricks.com/apps/01eabcdef123
```

### 2. Configure API Base URL

Open `00_API_Config.py` and update the `API_BASE_URL`:

```python
API_BASE_URL = "https://your-workspace.cloud.databricks.com/apps/01eabcdef123"
```

### 3. Run Tests

Open any test notebook and run it. Tests are organized by workload type:

**🔐 Authentication:** Tests automatically use OAuth authentication from your Databricks notebook session. No manual token setup required!

## Test Files

### Configuration
- **`00_API_Config.py`** - API configuration and helper functions
  - Contains `api_get()` and `api_post()` helper functions
  - Test connection to API
  - Reuse in all test notebooks with `%run ./00_API_Config`

### Cost Calculation Tests
- **`Test_API_01_JOBS_Classic.py`** - Test JOBS Classic cost calculation
  - ✅ All 3 clouds (AWS, Azure, GCP)
  - ✅ All tiers (STANDARD, PREMIUM, ENTERPRISE)
  - ✅ With/without Photon
  - ✅ All pricing tiers (on_demand, spot, reserved)
  - ✅ AWS payment options (no_upfront, partial_upfront, all_upfront)
  - ✅ Various usage patterns
  - ✅ Validation error testing

## Test Structure

Each test notebook follows this pattern:

```python
# 1. Load configuration
%run ./00_API_Config

# 2. Define helper functions
def test_workload_type(...):
    request_data = {...}
    response = api_post("/api/v1/calculate/...", request_data)
    # Validate and display results

# 3. Run test scenarios
test_workload_type(
    test_name="...",
    cloud="AWS",
    region="us-east-1",
    ...
)

# 4. Test validation errors
# Try invalid inputs and expect errors
```

## Example: Testing JOBS Classic

```python
# Run configuration
%run ./00_API_Config

# Test basic calculation
response = api_post("/api/v1/calculate/jobs-classic", {
    "cloud": "AWS",
    "region": "us-east-1",
    "tier": "PREMIUM",
    "driver_node_type": "m5.xlarge",
    "worker_node_type": "m5.xlarge",
    "num_workers": 10,
    "photon_enabled": true,
    "driver_pricing_tier": "on_demand",
    "worker_pricing_tier": "spot",
    "runs_per_day": 8,
    "avg_runtime_minutes": 60,
    "days_per_month": 30
})

# Check results
if response["success"]:
    cost = response["data"]["total_cost"]["cost_per_month"]
    print(f"Total monthly cost: ${cost:.2f}")
```

## Helper Functions

### `api_get(endpoint, params=None)`
Make GET requests to the API.

```python
# Get regions for AWS
regions = api_get("/api/v1/regions", {"cloud": "AWS"})
```

### `api_post(endpoint, data)`
Make POST requests to the API.

```python
# Calculate JOBS Classic cost
result = api_post("/api/v1/calculate/jobs-classic", {...})
```

### `print_response(response, title="API Response")`
Pretty print API responses.

```python
response = api_get("/health")
print_response(response, "Health Check")
```

## Test Coverage

### JOBS Classic (Test_API_01_JOBS_Classic.py)
- ✅ 9 success scenarios (different configs)
- ✅ 3 validation error scenarios
- ✅ All clouds, tiers, pricing options
- ✅ Photon enabled/disabled
- ✅ Light/medium/heavy usage patterns

### Coming Soon
- `Test_API_02_JOBS_Serverless.py` - JOBS Serverless tests
- `Test_API_03_DBSQL_Classic.py` - DBSQL Classic tests
- `Test_API_04_DBSQL_Pro.py` - DBSQL Pro tests
- `Test_API_05_DBSQL_Serverless.py` - DBSQL Serverless tests
- More workload types...

## Debugging

If tests fail, check:

1. **API URL is correct** - Update in `00_API_Config.py`
2. **API is deployed** - Run `databricks apps list`
3. **Pricing data exists** - Run pricing sync notebooks first
4. **Instance types exist** - Check `sync_ref_instance_dbu_rates` table
5. **VM costs exist** - Check `sync_pricing_vm_costs` table

## Notes

- All tests use the actual deployed API (no mocking)
- Tests call the database function `calculate_line_item_costs()`
- Results should match the function test results in `5_Function_Tests/`
- Tests validate both success cases and error handling

