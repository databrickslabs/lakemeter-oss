# ⚠️ Known Issues & Limitations

**Beta Version**: v0.9.0  
**Last Updated**: December 18, 2024

This document tracks known issues, limitations, and planned improvements for the Lakemeter API beta release.

---

## 🔴 Critical Issues (None Currently)

No critical issues identified at this time.

---

## 🟠 High Priority Limitations

### 1. No Rate Limiting
**Status**: Known Limitation  
**Impact**: API could be overwhelmed by excessive requests  
**Workaround**: Please avoid making >100 requests per minute  
**Planned Fix**: Add rate limiting in Release Candidate (v0.95)

**Why it matters**: Without rate limiting, a single client could degrade performance for everyone.

---

### 2. No Caching
**Status**: Known Limitation  
**Impact**: Every request hits the database, slower response times  
**Workaround**: Cache results on frontend for reference data (clouds, regions, etc.)  
**Planned Fix**: Add Redis caching for reference data in v1.0

**Why it matters**: Reference data rarely changes, but every request re-queries the database.

**Example - What to Cache on Frontend:**
```javascript
// These change rarely - safe to cache for 1 hour
- /api/v1/clouds
- /api/v1/regions
- /api/v1/instances/families
- /api/v1/dbsql/warehouse-types
- /api/v1/dbsql/warehouse-sizes

// These change occasionally - cache for 10 minutes
- /api/v1/instances/types
- /api/v1/model-serving/gpu-types
- /api/v1/fmapi/databricks-models/list

// Never cache these
- /api/v1/calculate/* (calculations should always be fresh)
- /api/v1/salesforce/* (data updates frequently)
```

---

### 3. No Batch Calculation Endpoint
**Status**: Planned Enhancement  
**Impact**: Must calculate costs one workload at a time  
**Workaround**: Make multiple sequential requests  
**Planned Fix**: Add `/api/v1/calculate/batch` endpoint in v1.1

**Why it matters**: For multi-workload scenarios (e.g., "Calculate cost for 10 different cluster configs"), you need to make 10 separate API calls.

**Ideal future API:**
```json
POST /api/v1/calculate/batch
{
  "calculations": [
    {"type": "jobs-classic", "params": {...}},
    {"type": "dbsql-serverless", "params": {...}},
    {"type": "model-serving", "params": {...}}
  ]
}
```

---

## 🟡 Medium Priority Issues

### 4. Limited GCP Instance Type Coverage
**Status**: Data Quality Issue  
**Impact**: Some GCP instance types may return "not found" errors  
**Workaround**: Use common instance types (n2-standard, n2-highmem families)  
**Planned Fix**: Complete GCP pricing data sync by v1.0

**Affected instance families:**
- C3 family (limited pricing data)
- C3D family (some regions missing)
- N2D family (some configurations incomplete)

**Recommendation**: Stick to these well-supported GCP families during beta:
- `n2-standard-*`
- `n2-highmem-*`
- `n2-highcpu-*`

---

### 5. FMAPI Model List May Lag
**Status**: Known Limitation  
**Impact**: Newly released models may not appear immediately  
**Workaround**: Check model availability in Databricks Console first  
**Planned Fix**: Implement daily model sync in v1.0

**Why it matters**: AI model providers (OpenAI, Anthropic, Google) release new models frequently. Our sync process runs weekly, so there may be a delay.

**Current sync schedule:**
- Databricks models: Weekly (Sundays)
- Proprietary models: Weekly (Sundays)

---

### 6. No Cost Comparison Endpoint
**Status**: Planned Enhancement  
**Impact**: Can't compare multiple configurations side-by-side  
**Workaround**: Calculate each config separately and compare in frontend  
**Planned Fix**: Add comparison endpoint in v1.1

**Ideal future API:**
```json
POST /api/v1/calculate/compare
{
  "baseline": {"type": "jobs-classic", "params": {...}},
  "alternatives": [
    {"type": "jobs-serverless", "params": {...}},
    {"type": "jobs-classic", "params": {...}} // with different instance types
  ]
}

Response:
{
  "baseline_cost": 1000,
  "alternatives": [
    {"cost": 800, "savings": 200, "savings_percent": 20},
    {"cost": 1200, "additional_cost": 200}
  ]
}
```

---

### 7. Pagination Doesn't Support Cursor-Based
**Status**: Known Limitation  
**Impact**: Offset-based pagination can miss items if data changes during pagination  
**Workaround**: For consistent results, fetch all pages quickly or use higher `limit`  
**Planned Fix**: Add cursor-based pagination option in v1.2

**Current limitation:**
```
Request 1: offset=0, limit=100 (returns items 1-100)
[New item added to database]
Request 2: offset=100, limit=100 (returns items 101-200, but you missed item 100)
```

---

## 🟢 Low Priority Items

### 8. No Swagger UI Authentication Persistence
**Status**: Swagger UI Limitation  
**Impact**: Must re-authenticate every time you refresh Swagger UI  
**Workaround**: Copy/paste token or use Postman/curl  
**Planned Fix**: Not planned (Swagger UI limitation)

**Pro tip**: Use Postman or your preferred API client for extensive testing. Save authentication token as environment variable.

---

### 9. Error Traceback Exposed in Responses
**Status**: Intentional (Beta Only)  
**Impact**: Internal implementation details visible in error responses  
**Workaround**: None needed  
**Planned Fix**: Remove detailed tracebacks for GA release (v1.0)

**Why it's there**: During beta, full tracebacks help debug issues quickly. In production, we'll sanitize these.

**Example:**
```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "...",
    "traceback": "Traceback (most recent call last): ..." // Will be removed for GA
  }
}
```

---

### 10. No API Versioning in URL
**Status**: Beta Decision  
**Impact**: API structure changes could break existing integrations  
**Workaround**: None needed during beta  
**Planned Fix**: Lock API structure for v1.0, introduce `/v2/` for breaking changes

**Current**: All endpoints at `/api/v1/*`  
**Future**: `/api/v1/*` (stable), `/api/v2/*` (new features with breaking changes)

---

### 11. Salesforce Data Refresh Frequency
**Status**: Known Limitation  
**Impact**: Salesforce data (accounts, opportunities, use cases) may be up to 24 hours old  
**Workaround**: For critical data, verify in Salesforce directly  
**Planned Fix**: Increase sync frequency to every 6 hours in v1.0

**Current sync schedule**: Daily at 2 AM UTC

---

### 12. No Webhook/Callback Support
**Status**: Planned Enhancement  
**Impact**: Cannot receive notifications when pricing data updates  
**Workaround**: Poll reference data endpoints periodically  
**Planned Fix**: Add webhook support in v1.2

**Future capability:**
```json
POST /api/v1/webhooks/subscribe
{
  "url": "https://your-app.com/webhook",
  "events": ["pricing_updated", "model_added"]
}
```

---

## 🐛 Recently Fixed Issues (v0.9.0)

### ✅ Azure Reserved VM Pricing (Fixed)
**Issue**: Azure reserved VM costs were 8,760x too high (annual instead of hourly)  
**Root Cause**: Azure Retail Prices API returns total reservation cost, not hourly rate  
**Fix**: Updated data sync notebook to divide by hours in term (8,760 for 1y, 26,280 for 3y)  
**Status**: Fixed in v0.9.0, database corrected (20,042 rows updated)

---

### ✅ FMAPI Endpoints Returning $0 (Fixed)
**Issue**: FMAPI Databricks and Proprietary endpoints always returned $0 cost  
**Root Cause**: Wrong `workload_type` parameter and missing usage parameters  
**Fix**: Changed to `FMAPI_DATABRICKS` and `FMAPI_PROPRIETARY`, added default usage params  
**Status**: Fixed in v0.9.0

---

### ✅ DBSQL Serverless Warehouse Size Validation (Fixed)
**Issue**: Serverless warehouse sizes were validated against Classic/Pro config table  
**Root Cause**: Used wrong table for validation (hardware specs vs DBU rates)  
**Fix**: Modified validator to use `sync_product_dbsql_rates` for SERVERLESS  
**Status**: Fixed in v0.9.0

---

### ✅ AWS Reserved Pricing Returning $0 VM Costs (Fixed)
**Issue**: AWS reserved pricing with `payment_option="NA"` returned $0 VM costs  
**Root Cause**: Invalid payment option for reserved pricing on AWS  
**Fix**: Added cloud-aware payment option validation (AWS reserved requires no_upfront/partial_upfront/all_upfront)  
**Status**: Fixed in v0.9.0

---

## 📋 Workarounds Summary

### Quick Reference

| Issue | Workaround | Timeline |
|-------|-----------|----------|
| No rate limiting | Limit to <100 req/min | v0.95 |
| No caching | Cache reference data on frontend | v1.0 |
| No batch calculations | Make sequential requests | v1.1 |
| Limited GCP coverage | Use n2-* instance families | v1.0 |
| FMAPI model lag | Check Databricks Console | v1.0 |
| Offset pagination issues | Fetch pages quickly | v1.2 |
| Swagger token persistence | Use Postman/curl | No fix |
| Salesforce data staleness | Verify in Salesforce if critical | v1.0 |

---

## 🚧 Limitations by Design

These are intentional design decisions that won't change:

### 1. OAuth Authentication Required
**Rationale**: Security and user context  
**Alternative**: Use service account token for server-to-server

### 2. PostgreSQL Function for Calculations
**Rationale**: Centralized business logic, easier to maintain  
**Alternative**: None planned

### 3. No DELETE/UPDATE Endpoints
**Rationale**: Read-only API for cost calculation and reference data  
**Alternative**: Use database directly for data management

### 4. Cloud-Specific Validation
**Rationale**: Each cloud provider has different pricing models  
**Alternative**: None - this is a feature, not a limitation

---

## 📞 Reporting New Issues

Found an issue not listed here?

1. **Check this document first** - It may already be known
2. **Check GitHub Issues** - https://github.com/muharandy/promptsizer/issues
3. **Review Beta Testing Guide** - [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)
4. **Report with template** - Use issue templates from testing guide

**When reporting, include:**
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Request/response details
- Environment info

---

## 🎯 Roadmap Summary

### v0.95 (Release Candidate) - Mid-January 2025
- ✅ Add rate limiting (100 req/min per user)
- ✅ Add basic caching for reference data
- ✅ Complete GCP pricing data
- ✅ Increase FMAPI sync frequency

### v1.0 (GA Release) - End of January 2025
- ✅ Remove error tracebacks from responses
- ✅ Performance optimization
- ✅ Complete documentation
- ✅ Increase Salesforce sync frequency
- ✅ Lock API structure (no breaking changes)

### v1.1 (Enhancement Release) - February 2025
- ✅ Batch calculation endpoint
- ✅ Cost comparison endpoint
- ✅ Enhanced error messages

### v1.2 (Advanced Features) - March 2025
- ✅ Cursor-based pagination
- ✅ Webhook support
- ✅ Advanced filtering options

---

## 📝 Notes

- This document is updated regularly during beta
- All known issues are tracked in GitHub
- Critical issues are escalated immediately
- Your feedback helps us prioritize fixes

**Last reviewed**: December 18, 2024  
**Next review**: December 25, 2024

