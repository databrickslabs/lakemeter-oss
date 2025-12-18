# 🤖 AI Agent Integration Guide - Lakemeter API

## Quick Start for AI Agents

**TL;DR**: Yes, your AI agent can directly consume the OpenAPI spec!

---

## Option 1: Read OpenAPI Spec Directly (Recommended for Agents)

### Get the OpenAPI JSON Spec:
```bash
GET https://lakemeter-api-335310294452632.aws.databricksapps.com/openapi.json
Authorization: Bearer <your_databricks_token>
```

### Get Interactive Swagger UI:
```
https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
```

**What you get:**
- ✅ All endpoint definitions
- ✅ Request/response schemas
- ✅ Parameter types and validation
- ✅ Example values
- ✅ Machine-readable format

---

## Option 2: Read the Documentation (Recommended for Context)

See `API_DOCUMENTATION.md` for:
- 📚 Business logic and validation rules
- ⚠️ Cloud-specific behaviors (AWS vs Azure vs GCP)
- 💡 Important gotchas (e.g., "driver cannot be spot")
- 🎯 Best practices and patterns
- 📝 Real-world usage examples

---

## Recommended Approach: **BOTH** 🎉

1. **Start with OpenAPI spec** to understand:
   - Available endpoints
   - Required/optional parameters
   - Data types and formats
   - Response structures

2. **Read API_DOCUMENTATION.md** for:
   - Cloud-specific payment option rules
   - Flexible usage parameters pattern (run-based vs direct hours)
   - Error handling patterns
   - Common pitfalls and how to avoid them

---

## Key Things OpenAPI Won't Tell You

### 1. **Payment Options are Cloud-Specific**
```
AWS reserved pricing → Must use: no_upfront, partial_upfront, all_upfront
Azure/GCP → Always use: NA
```

### 2. **Driver Cannot Be Spot**
For classic workloads, `driver_pricing_tier` cannot be `"spot"` (stability requirement).

### 3. **Flexible Usage Parameters**
Most calculation endpoints accept EITHER:
- `runs_per_day` + `avg_runtime_minutes` + `days_per_month`
- OR `hours_per_month`

(Never both simultaneously)

### 4. **Serverless Always Has Photon Enabled**
Don't send `photon_enabled` parameter for serverless endpoints - it's always true.

### 5. **DBSQL Warehouse Size Validation**
Different validation logic for CLASSIC/PRO vs SERVERLESS warehouse types.

### 6. **Azure Has No ENTERPRISE Tier**
`tier` parameter validation is cloud-aware.

---

## Authentication for Your Agent

### Get Databricks Token:

**From Databricks Notebook:**
```python
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
```

**From Local/External (with Databricks CLI configured):**
```bash
databricks auth token --host https://your-workspace.cloud.databricks.com
```

### Use Token in Requests:
```bash
Authorization: Bearer <token>
```

---

## Testing the API

### 1. Health Check (No Auth Required):
```bash
curl https://lakemeter-api-335310294452632.aws.databricksapps.com/health
```

### 2. Simple Reference Data (Auth Required):
```bash
curl -H "Authorization: Bearer <token>" \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/clouds
```

### 3. Cost Calculation (Auth Required):
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
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

---

## API Response Pattern

All endpoints follow this consistent structure:

### Success Response:
```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response:
```json
{
  "success": false,
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "field": "parameter_name",
    "allowed_values": ["option1", "option2"]
  }
}
```

**Pro Tip**: Always check for `allowed_values` in error responses - use them to show users what's valid!

---

## Endpoint Categories (Tags in Swagger)

### Reference Data APIs:
- `Salesforce` - Accounts, Opportunities, Use Cases
- `Geography` - Clouds, Regions, Tiers
- `Compute - Instance Types` - Instance types, families, VM pricing
- `DBSQL` - Warehouse types, sizes, configs
- `Model Serving` - GPU types
- `FMAPI` - Databricks & Proprietary models
- `Vector Search` - Modes
- `Lakebase` - CU sizes
- `Photon` - Multipliers
- `Serverless` - Mode multipliers
- `DBU Pricing` - Base rates

### Cost Calculation APIs:
- `Cost Calculation` - All 13 calculation endpoints

---

## Rate Limiting

**Current**: No rate limits  
**Recommendation**: Avoid excessive parallel requests (be nice to the database)

---

## For Frontend Development

### Typical Workflow:

1. **Load Dropdowns** (on page load):
   ```
   GET /api/v1/clouds
   GET /api/v1/regions?cloud=AWS
   GET /api/v1/pricing-tiers?cloud=AWS
   GET /api/v1/instances/types?cloud=AWS&region=us-east-1
   ```

2. **User Fills Form** (with dynamic validation):
   - Use `allowed_values` from errors to populate dropdowns
   - Show/hide payment options based on cloud selection
   - Disable "spot" for driver pricing tier

3. **Calculate Cost** (on form submit):
   ```
   POST /api/v1/calculate/jobs-classic
   ```

4. **Display Results**:
   - Show breakdown: DBU cost + VM cost = Total
   - Show configuration summary
   - Show usage calculation

---

## Common Pitfalls to Avoid

### ❌ Don't:
- Send `photon_enabled` for serverless endpoints
- Use `spot` for `driver_pricing_tier`
- Mix run-based and direct hours parameters
- Use `no_upfront`/`partial_upfront`/`all_upfront` for Azure/GCP
- Use `NA` for AWS reserved pricing
- Include `dlt_edition` for DLT Serverless
- Assume ENTERPRISE tier works for Azure

### ✅ Do:
- Validate cloud-specific payment options
- Check `allowed_values` in error responses
- Use either run-based OR hours_per_month (not both)
- Pass node types even for serverless (needed for DBU calculation)
- Handle errors gracefully with helpful messages

---

## Need Help?

1. **Check Swagger UI**: `https://lakemeter-api-335310294452632.aws.databricksapps.com/docs`
2. **Read API_DOCUMENTATION.md**: Full endpoint reference with examples
3. **Check Error Messages**: They include helpful hints and allowed values
4. **Test in Swagger**: Interactive testing with "Try it out" button

---

## Summary for AI Agents

**Yes, you can read the OpenAPI spec directly!**

But for best results:
1. Parse OpenAPI spec for endpoint structure
2. Read `API_DOCUMENTATION.md` for business logic and gotchas
3. Test a few endpoints to understand the pattern
4. Build with confidence! The API is fully validated and returns helpful errors.

🚀 **Happy Building!**

