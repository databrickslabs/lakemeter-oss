# ❓ Frequently Asked Questions (FAQ)

**Last Updated**: December 18, 2024  
**Beta Version**: v0.9.0

---

## 🔐 Authentication & Access

### Q: How do I get an OAuth token?

**A:** There are two ways:

**From Databricks Notebook:**
```python
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
```

**From Local Terminal (if CLI configured):**
```bash
databricks auth token --host https://your-workspace.cloud.databricks.com
```

---

### Q: How long does the token last?

**A:** By default, Databricks OAuth tokens expire after 1 hour. You'll need to refresh your token periodically.

**Pro tip**: In your application, implement token refresh logic or catch 401 errors and re-authenticate.

---

### Q: Can I use a service account token?

**A:** Yes! If you're building a backend service, you can use a Databricks service principal token instead of a user token. This provides longer-lived authentication and doesn't require user interaction.

---

### Q: Do I need to authenticate for all endpoints?

**A:** Almost all endpoints require authentication. The only exception is `/health` which is public for monitoring.

---

## 💰 Cost Calculation

### Q: Why are my costs different from Databricks Console?

**A:** Several possible reasons:

1. **Pricing tier mismatch** - Ensure you're using the correct tier (STANDARD/PREMIUM/ENTERPRISE)
2. **Region mismatch** - VM costs vary significantly by region
3. **Photon not accounted for** - Photon adds multipliers to DBU costs
4. **Payment option** - Reserved pricing differs from on-demand
5. **Usage calculation** - Double-check hours per month calculation

**Debug tip**: Use Swagger UI to see the full response breakdown (DBU rate, VM costs, multipliers).

---

### Q: What's the difference between run-based and direct hours?

**A:** Two ways to specify usage:

**Run-based (automatic calculation):**
```json
{
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
}
```
API calculates: `hours_per_month = (8 × 60 × 30) / 60 = 240`

**Direct hours (you calculate):**
```json
{
  "hours_per_month": 240
}
```

Use whichever is more intuitive for your use case. Results are identical.

---

### Q: Can I calculate costs for multiple workloads at once?

**A:** Not yet. Currently, you need to make separate API calls for each workload. Batch calculation is planned for v1.1.

**Workaround**: Make concurrent requests (within rate limits) to speed up multiple calculations.

---

### Q: Why do I get $0 cost for serverless workloads?

**A:** You still need to provide `driver_node_type`, `worker_node_type`, and `num_workers` even for serverless. These are used to calculate the base DBU rate (though there are no VM costs).

---

### Q: How accurate are the cost calculations?

**A:** Very accurate for most configurations:
- ✅ DBU pricing is synced weekly from Databricks
- ✅ VM pricing is synced daily from cloud providers
- ✅ Calculations match production workloads
- ⚠️ Some GCP instance types may have incomplete data (see [KNOWN_ISSUES.md](./KNOWN_ISSUES.md))

**For critical budgeting**: Cross-reference with at least one production workload first.

---

## 🌍 Cloud-Specific Questions

### Q: Why can't I use ENTERPRISE tier on Azure?

**A:** Azure doesn't offer the ENTERPRISE pricing tier. Only STANDARD and PREMIUM are available.

The API validates this and returns an error if you try to use ENTERPRISE on Azure.

---

### Q: Why do AWS and Azure/GCP have different payment options?

**A:** AWS offers granular reserved instance payment options:
- No Upfront (pay monthly)
- Partial Upfront (some upfront, rest monthly)
- All Upfront (pay everything upfront, lowest cost)

Azure and GCP use simplified reserved pricing without upfront payment options.

**In the API:**
- **AWS on-demand/spot**: `"payment_option": "NA"`
- **AWS reserved**: `"no_upfront"`, `"partial_upfront"`, or `"all_upfront"`
- **Azure/GCP (all)**: `"payment_option": "NA"`

---

### Q: Which cloud is cheapest?

**A:** It depends! Factors include:
- **Pricing tier** - Different clouds have different tier premiums
- **Region** - Costs vary significantly by region
- **Instance type** - Instance type availability and pricing differ
- **Commitment level** - Reserved pricing varies by cloud
- **Workload type** - Some workload types are priced differently

**Use the API to compare**: Calculate the same workload configuration on each cloud.

---

## 🔢 Parameters & Validation

### Q: Why can't I use spot instances for the driver?

**A:** Driver nodes need to be stable because they orchestrate the entire workload. If the driver is preempted (terminated), the entire job fails.

This is a Databricks best practice, enforced by the API.

---

### Q: What instance types are available?

**A:** Use the `/api/v1/instances/types` endpoint to get available instance types for your cloud and region.

You can filter by:
- Instance family (Compute Optimized, Memory Optimized, etc.)
- vCPU range
- Memory range
- DBU rate range

---

### Q: How do I know what warehouse sizes are valid?

**A:** Use the `/api/v1/dbsql/warehouse-sizes` endpoint to get all valid sizes with their DBU rates.

For serverless, sizes are validated against actual serverless offerings (which may differ from Classic/Pro).

---

### Q: Can I use reserved pricing for workers but on-demand for driver?

**A:** Yes! Driver and worker pricing tiers are independent:

```json
{
  "driver_pricing_tier": "on_demand",
  "worker_pricing_tier": "reserved_1y",
  "driver_payment_option": "NA",
  "worker_payment_option": "no_upfront"  // AWS only
}
```

This is actually a common cost optimization strategy.

---

## 🤖 AI & ML Workloads

### Q: What's the difference between FMAPI Databricks and Proprietary?

**A:** 

**FMAPI Databricks** (`/api/v1/calculate/fmapi-databricks`):
- Databricks-hosted models (llama, gemma, etc.)
- Simple model selection
- Rate types: `input_token`, `output_token`, `provisioned_scaling`, `provisioned_entry`

**FMAPI Proprietary** (`/api/v1/calculate/fmapi-proprietary`):
- External provider models (OpenAI, Anthropic, Google)
- Additional parameters: `provider`, `endpoint_type`, `context_length`
- Rate types: `input_token`, `output_token`, `cache_read`, `cache_write`, `batch_inference`

---

### Q: How do I calculate token-based costs?

**A:** Token-based pricing charges per million tokens:

```json
{
  "model": "claude-sonnet-4-5",
  "rate_type": "input_token",
  "quantity": 1000000  // 1 million tokens
}
```

The API returns cost for your specified quantity.

---

### Q: How do I calculate provisioned model costs?

**A:** Provisioned pricing charges per hour of server time:

```json
{
  "model": "llama-3-3-70b",
  "rate_type": "provisioned_scaling",
  "quantity": 730  // hours per month
}
```

---

### Q: What GPU types are available for Model Serving?

**A:** Use `/api/v1/model-serving/gpu-types?cloud=AWS` to get available GPUs for your cloud.

Options vary by cloud:
- **AWS**: T4, A10G variants, A100 variants
- **Azure**: T4, A100 variants
- **GCP**: G2 standard, limited A100

---

## 📊 Data & Reference APIs

### Q: How often is pricing data updated?

**A:** Update frequencies:
- **DBU pricing**: Weekly (Sundays)
- **VM pricing**: Daily (2 AM UTC)
- **FMAPI models**: Weekly (Sundays)
- **Salesforce data**: Daily (2 AM UTC)

**For GA release**: Planning to increase most to daily or more frequently.

---

### Q: Why don't I see my newly created Salesforce opportunity?

**A:** Salesforce data syncs once daily at 2 AM UTC. New opportunities may take up to 24 hours to appear.

**For critical data**: Verify directly in Salesforce.

---

### Q: Can I filter instance types by vCPU or memory?

**A:** Yes! Use query parameters:

```
GET /api/v1/instances/types?cloud=AWS&region=us-east-1&min_vcpus=8&max_vcpus=16&min_memory_gb=32&max_memory_gb=64
```

Also supports:
- `instance_family` (exact match)
- `min_dbu_rate` / `max_dbu_rate`
- Pagination with `limit` and `offset`

---

## 🚀 Performance & Limits

### Q: How fast is the API?

**A:** Typical response times:
- **Reference data**: 100-300ms
- **Simple calculations**: 200-500ms
- **Complex calculations**: 500-1000ms

**Note**: No caching yet, so every request hits the database. Caching coming in v1.0.

---

### Q: Are there rate limits?

**A:** Not in beta. Please be reasonable and limit to <100 requests per minute.

**Coming in v0.95**: 100 requests per minute per user.

---

### Q: Can I make concurrent requests?

**A:** Yes, within reason. The database can handle concurrent requests, but avoid overwhelming it with hundreds of simultaneous calls.

**Recommendation**: For bulk calculations, limit to 10-20 concurrent requests.

---

### Q: Should I cache API responses?

**A:** Yes, especially for reference data!

**Safe to cache (1 hour):**
- Clouds (`/api/v1/clouds`)
- Regions (`/api/v1/regions`)
- Instance families (`/api/v1/instances/families`)
- Warehouse types/sizes (`/api/v1/dbsql/*`)

**Cache for 10 minutes:**
- Instance types (may change)
- GPU types (new GPUs added occasionally)

**Never cache:**
- Cost calculations (always use fresh data)
- Salesforce data (updates frequently)

See [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) for detailed caching recommendations.

---

## 🛠️ Development & Integration

### Q: Is there a Postman collection?

**A:** Not yet, but you can import the OpenAPI spec:

1. In Postman: File → Import
2. Paste URL: `https://lakemeter-api-335310294452632.aws.databricksapps.com/openapi.json`
3. Configure authorization header with your token

**Coming in v1.0**: Pre-built Postman collection with examples.

---

### Q: Can my AI agent use this API?

**A:** Yes! The API is designed for both human and AI agent consumption.

See [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md) for:
- How to read the OpenAPI spec
- What the spec won't tell you (business rules)
- Common patterns and best practices

---

### Q: What frontend frameworks work best?

**A:** Any framework that can make HTTP requests! The API is framework-agnostic.

**Tested with:**
- React (fetch, axios)
- Vue (axios, fetch)
- Angular (HttpClient)
- Python (requests)
- curl / Postman

---

### Q: Can I run this API locally for development?

**A:** The API is deployed as a Databricks App. For local development:

1. Use the deployed API (recommended for beta)
2. Mock the API responses in your frontend
3. Contact the team for local deployment instructions

---

## 🐛 Troubleshooting

### Q: I'm getting 401 Unauthorized errors

**A:** Token issue. Check:
1. Token is valid (not expired)
2. Token is in `Authorization: Bearer TOKEN` header
3. Token has correct format (no extra quotes, spaces, etc.)

**Generate fresh token**:
```python
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
```

---

### Q: I'm getting "Invalid Instance Type" errors

**A:** Instance type not available for your cloud/region.

**Solution:**
1. Check the error message for `allowed_values` (lists first 20 valid types)
2. Use `/api/v1/instances/types` to get complete list
3. Verify cloud and region are correct

---

### Q: Why is my reserved pricing returning $0?

**A:** Payment option validation issue (likely AWS).

**For AWS reserved pricing:**
- ❌ `"payment_option": "NA"` → Returns $0
- ✅ `"payment_option": "no_upfront"` → Correct

**For Azure/GCP:**
- ✅ `"payment_option": "NA"` → Always use this

---

### Q: The API is slow / timing out

**A:** Several possible causes:

1. **Large pagination** - Reduce `limit` parameter
2. **Database load** - Wait a moment and retry
3. **Complex query** - Simplify filters
4. **Network issues** - Check your connection

**Still having issues?** Report it! See [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md).

---

## 📈 Beta Program

### Q: How long is the beta period?

**A:** Approximately 4 weeks (December 18, 2024 - January 15, 2025).

**Timeline:**
- Weeks 1-2: Initial testing & feedback
- Week 3: Integration testing
- Week 4: Performance & polish
- GA Release: Late January 2025

---

### Q: Will the API change during beta?

**A:** Possibly, based on feedback. We'll minimize breaking changes, but beta is the time to iterate.

**Any breaking changes will be:**
- Clearly documented
- Communicated in advance
- Included in migration guides

---

### Q: How do I report issues or suggest features?

**A:** Three ways:

1. **GitHub Issues** (recommended): https://github.com/muharandy/promptsizer/issues
2. **Beta Testing Guide**: Follow templates in [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)
3. **Direct feedback**: Contact API team

---

### Q: Will my feedback be considered?

**A:** Absolutely! Beta tester feedback directly shapes the GA release.

**Priority areas:**
- Critical bugs (fixed immediately)
- Calculation accuracy issues (high priority)
- Error message clarity (medium priority)
- Feature requests (evaluated for v1.1+)

---

## 📚 Documentation

### Q: Where do I find complete API documentation?

**A:** Several resources:

- **Quick Start**: [GETTING_STARTED.md](./GETTING_STARTED.md)
- **Complete API Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **AI Agent Guide**: [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md)
- **Interactive Docs**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
- **Known Issues**: [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)
- **Release Notes**: [BETA_RELEASE_NOTES.md](./BETA_RELEASE_NOTES.md)

---

### Q: Is there a video tutorial?

**A:** Not yet. Planned for GA release.

**For now**: Use [GETTING_STARTED.md](./GETTING_STARTED.md) for step-by-step walkthrough.

---

### Q: Are there code examples?

**A:** Yes! Multiple resources:

1. **Getting Started**: Basic examples for curl, Python, JavaScript
2. **API Documentation**: Detailed examples for each endpoint
3. **Swagger UI**: Interactive "Try it out" for all endpoints
4. **API Tests folder**: Real test code in GitHub

---

## 💡 Best Practices

### Q: What's the recommended workflow for building a cost calculator?

**A:** Typical flow:

1. **On page load**: Fetch reference data (clouds, regions) - Cache for 1 hour
2. **On cloud selection**: Fetch regions for that cloud - Cache per cloud
3. **On region selection**: Fetch instance types - Cache per cloud+region
4. **As user types**: Validate selections (use cached data)
5. **On form submit**: Calculate cost (always fetch fresh)
6. **Display results**: Show breakdown (DBU, VM, total)

---

### Q: Should I validate on frontend or rely on API validation?

**A:** Both!

**Frontend validation (recommended):**
- Fetch valid options first (regions, instance types, etc.)
- Only show valid options in dropdowns
- Disable invalid combinations (e.g., spot for driver)
- Provide instant feedback

**API validation (always happens):**
- Catches edge cases
- Provides authoritative error messages
- Includes `allowed_values` for corrections

**Best approach**: Frontend validation for UX, API validation as safety net.

---

### Q: How should I handle errors?

**A:** Parse error responses for helpful info:

```javascript
if (!response.ok) {
  const error = await response.json();
  
  // Show field-specific error
  highlightField(error.detail.field);
  
  // If allowed values provided, let user pick
  if (error.detail.allowed_values) {
    showDropdown(error.detail.field, error.detail.allowed_values);
  }
  
  // Show clear message
  showError(error.detail.message);
}
```

---

## ❓ Still Have Questions?

**Check these resources first:**
1. [GETTING_STARTED.md](./GETTING_STARTED.md) - Quick start guide
2. [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - Complete reference
3. [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) - Current limitations
4. [Swagger UI](https://lakemeter-api-335310294452632.aws.databricksapps.com/docs) - Interactive docs

**Still stuck?**
- Search existing GitHub issues
- Create a new issue with details
- Contact the API team

**Your question might help others!** Consider suggesting it as an addition to this FAQ.

---

**Last Updated**: December 18, 2024  
**Next Review**: December 25, 2024

