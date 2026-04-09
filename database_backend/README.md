# 🚀 Lakemeter API - Beta Release

**Comprehensive Databricks Workload Cost Calculation API**

[![Beta Version](https://img.shields.io/badge/version-0.9.0-blue)](./BETA_RELEASE_NOTES.md)
[![Status](https://img.shields.io/badge/status-Beta%20Testing-yellow)](./BETA_TESTING_GUIDE.md)
[![API Docs](https://img.shields.io/badge/docs-Swagger-green)](https://lakemeter-api-335310294452632.aws.databricksapps.com/docs)

---

## 📖 Overview

Lakemeter API provides accurate, real-time cost calculations for Databricks workloads across AWS, Azure, and GCP. Built for developers, finance teams, and AI agents, it offers comprehensive pricing data and smart validation to help you optimize Databricks spending.

### ✨ Key Features

- **13 Calculation Endpoints** - JOBS, All-Purpose, DBSQL, DLT, Model Serving, FMAPI, Vector Search, Lakebase
- **30+ Reference Data APIs** - Clouds, regions, instance types, warehouses, GPUs, AI models
- **Cloud-Aware Validation** - Different rules for AWS vs Azure vs GCP
- **Flexible Usage Parameters** - Run-based or direct hours calculation
- **Comprehensive Error Messages** - Includes allowed values for easy debugging
- **AI Agent Ready** - Machine-readable OpenAPI spec

---

## 🎯 Quick Links

### 📚 Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [**GETTING_STARTED.md**](./GETTING_STARTED.md) | Get up and running in 5 minutes | Everyone |
| [**API_DOCUMENTATION.md**](./API_DOCUMENTATION.md) | Complete API reference with examples | Developers |
| [**AI_AGENT_GUIDE.md**](./AI_AGENT_GUIDE.md) | How AI agents can consume the API | AI/ML Engineers |
| [**BETA_TESTING_GUIDE.md**](./BETA_TESTING_GUIDE.md) | What to test and how to report issues | Beta Testers |
| [**KNOWN_ISSUES.md**](./KNOWN_ISSUES.md) | Current limitations and workarounds | Everyone |
| [**FAQ.md**](./FAQ.md) | Frequently asked questions | Everyone |
| [**BETA_RELEASE_NOTES.md**](./BETA_RELEASE_NOTES.md) | What's in this release | Everyone |

### 🔗 API Resources

- **Base URL**: https://lakemeter-api-335310294452632.aws.databricksapps.com
- **Swagger UI**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
- **OpenAPI Spec**: https://lakemeter-api-335310294452632.aws.databricksapps.com/openapi.json
- **GitHub Repo**: https://github.com/muharandy/promptsizer/tree/database_backend/database_backend

---

## ⚡ Quick Start

### 1. Get Your OAuth Token

```python
# From Databricks Notebook
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
```

### 2. Make Your First API Call

```bash
# Health check (no auth required)
curl https://lakemeter-api-335310294452632.aws.databricksapps.com/health

# Get available clouds (auth required)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/clouds
```

### 3. Calculate a Cost

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
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

**See [GETTING_STARTED.md](./GETTING_STARTED.md) for detailed walkthrough.**

---

## 📊 API Endpoints Overview

### Cost Calculation Endpoints

| Endpoint | Description | VM Costs? |
|----------|-------------|-----------|
| `POST /api/v1/calculate/jobs-classic` | Classic JOBS clusters | ✅ Yes |
| `POST /api/v1/calculate/jobs-serverless` | Serverless JOBS | ❌ No (DBU only) |
| `POST /api/v1/calculate/all-purpose-classic` | Classic interactive clusters | ✅ Yes |
| `POST /api/v1/calculate/all-purpose-serverless` | Serverless interactive | ❌ No |
| `POST /api/v1/calculate/dbsql-classic-pro` | DBSQL Classic/Pro warehouses | ✅ Yes |
| `POST /api/v1/calculate/dbsql-serverless` | DBSQL Serverless warehouses | ❌ No |
| `POST /api/v1/calculate/dlt-classic` | Classic Delta Live Tables | ✅ Yes |
| `POST /api/v1/calculate/dlt-serverless` | Serverless DLT | ❌ No |
| `POST /api/v1/calculate/model-serving` | GPU-based model serving | ❌ No (DBU only) |
| `POST /api/v1/calculate/fmapi-databricks` | Databricks FMAPI models | ❌ No |
| `POST /api/v1/calculate/fmapi-proprietary` | OpenAI, Anthropic, Google models | ❌ No |
| `POST /api/v1/calculate/vector-search` | Vector database search | ❌ No |
| `POST /api/v1/calculate/lakebase` | Managed PostgreSQL | ❌ No |

### Reference Data Endpoints

**Geography**
- `GET /api/v1/clouds` - Available clouds (AWS, Azure, GCP)
- `GET /api/v1/regions` - Regions by cloud
- `GET /api/v1/pricing-tiers` - Pricing tiers by cloud

**Compute - Instance Types**
- `GET /api/v1/instances/types` - Instance types with filters
- `GET /api/v1/instances/families` - Instance families
- `GET /api/v1/instances/vm-costs` - Detailed VM pricing
- `GET /api/v1/instances/vm-pricing-options` - Available pricing options

**DBSQL**
- `GET /api/v1/dbsql/warehouse-types` - Warehouse types
- `GET /api/v1/dbsql/warehouse-sizes` - Sizes with DBU rates
- `GET /api/v1/dbsql/warehouse-hardware` - Hardware specs (Classic/Pro)
- `GET /api/v1/dbsql/warehouse-vm-costs` - VM costs by configuration

**Model Serving**
- `GET /api/v1/model-serving/gpu-types` - Available GPUs with DBU rates

**FMAPI**
- `GET /api/v1/fmapi/databricks-models/list` - Databricks models
- `GET /api/v1/fmapi/databricks-models` - Databricks model pricing
- `GET /api/v1/fmapi/proprietary-models/list` - Proprietary models by provider
- `GET /api/v1/fmapi/proprietary-models/options` - Options for specific model
- `GET /api/v1/fmapi/proprietary-models` - Proprietary model pricing

**Other**
- `GET /api/v1/vector-search/list` - Vector Search modes
- `GET /api/v1/lakebase/list` - Lakebase CU sizes
- `GET /api/v1/photon/list` - Photon-enabled SKU types
- `GET /api/v1/photon/multipliers` - Photon multipliers
- `GET /api/v1/serverless/modes` - Serverless mode multipliers
- `GET /api/v1/dbu-pricing/base` - Base DBU pricing rates

**Salesforce**
- `GET /api/v1/salesforce/accounts` - Accounts with pagination
- `GET /api/v1/salesforce/opportunities` - Opportunities by account
- `GET /api/v1/salesforce/use-cases` - Use cases by account

**See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete reference.**

---

## 🎯 Use Cases

### 1. Cost Calculator UI

Build a web-based cost calculator:
1. Fetch dropdown options (clouds, regions, instance types)
2. User selects configuration
3. Validate selections in real-time
4. Calculate and display costs with breakdown

### 2. Budget Planning

Help finance teams forecast Databricks spending:
1. Define workload profiles (dev, staging, prod)
2. Calculate monthly costs for each
3. Compare scenarios (serverless vs classic, cloud comparisons)
4. Generate budget reports

### 3. Cost Optimization

Identify savings opportunities:
1. Calculate current workload costs
2. Compare alternative configurations (instance types, reserved pricing)
3. Analyze savings from serverless migration
4. Recommend optimal pricing strategies

### 4. AI-Powered Cost Assistant

Build an AI agent that answers cost questions:
1. Agent reads OpenAPI spec to understand endpoints
2. User asks: "How much would it cost to run 10 JOBS clusters on AWS?"
3. Agent makes API calls to calculate accurate costs
4. Returns detailed breakdown and recommendations

---

## 🔑 Key Concepts

### Cloud-Specific Payment Options

**AWS:**
- On-demand/Spot → `"payment_option": "NA"`
- Reserved (1y/3y) → `"no_upfront"`, `"partial_upfront"`, or `"all_upfront"`

**Azure/GCP:**
- All pricing tiers → `"payment_option": "NA"`

### Flexible Usage Parameters

Most endpoints accept EITHER:

**Run-based (automatic):**
```json
{
  "runs_per_day": 8,
  "avg_runtime_minutes": 60,
  "days_per_month": 30
}
```

**Direct hours (manual):**
```json
{
  "hours_per_month": 240
}
```

### Serverless Considerations

- ✅ Photon always enabled (not a parameter)
- ✅ No VM costs (DBU only)
- ✅ Still requires node types (for DBU calculation)
- ✅ Serverless mode multipliers: standard (1x), performance (2x)

### Driver Pricing Rules

- ❌ Driver cannot use `spot` pricing (stability requirement)
- ✅ Driver can use on-demand or reserved pricing
- ✅ Workers can use any pricing tier (including spot)

---

## ⚠️ Known Limitations

### Beta Limitations
- **No rate limiting** - Please limit to <100 req/min
- **No caching** - All requests hit database (cache reference data on frontend)
- **No batch calculations** - Calculate one workload at a time

### Data Quality
- ✅ **FIXED**: Azure reserved VM pricing (was 8760x too high)
- ⚠️ Some GCP instance types may have incomplete data
- ⚠️ FMAPI model list syncs weekly (may lag new releases)

**See [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) for complete list and workarounds.**

---

## 🧪 Beta Testing

### Beta Period

**Duration**: December 18, 2024 - January 15, 2025 (4 weeks)

**Objectives:**
1. Validate cost accuracy across all workload types
2. Test frontend integration workflows
3. Verify error messages are helpful
4. Assess performance under realistic load
5. Identify missing features or documentation gaps

### How to Participate

1. **Read** [GETTING_STARTED.md](./GETTING_STARTED.md) - Get up to speed
2. **Test** [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md) - Follow testing checklist
3. **Report** issues via GitHub - Use provided templates
4. **Ask** questions via FAQ or new issues

### What We Need From You

- ✅ Test at least 5 different calculation endpoints
- ✅ Test both success and error scenarios
- ✅ Provide feedback on accuracy, errors, and documentation
- ✅ Report any critical or high-priority issues
- ✅ Suggest improvements or missing features

**See [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md) for detailed instructions.**

---

## 📅 Roadmap

### v0.95 (Release Candidate) - Mid-January 2025
- Add rate limiting (100 req/min per user)
- Add basic caching for reference data
- Complete GCP pricing data
- Increase FMAPI model sync frequency

### v1.0 (GA Release) - End of January 2025
- Remove error tracebacks from responses
- Performance optimization
- Complete documentation (video tutorials, Postman collection)
- Increase Salesforce sync frequency
- Lock API structure (no breaking changes)

### v1.1 (Enhancement Release) - February 2025
- Batch calculation endpoint
- Cost comparison endpoint
- Enhanced error messages

### v1.2 (Advanced Features) - March 2025
- Cursor-based pagination
- Webhook support for pricing updates
- Advanced filtering options

---

## 🛠️ Technical Details

### Stack
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (Databricks Lakebase)
- **Authentication**: Databricks OAuth
- **Deployment**: Databricks Apps
- **Documentation**: OpenAPI 3.0

### Architecture
- **Calculation Engine**: PostgreSQL function (`lakemeter.calculate_line_item_costs`)
- **Validation**: Modular validators with cloud-aware rules
- **Error Handling**: Consistent JSON format with detailed messages
- **Data Sync**: Automated daily/weekly refreshes from source systems

---

## 📞 Support & Feedback

### Documentation
- **Quick Start**: [GETTING_STARTED.md](./GETTING_STARTED.md)
- **Complete Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **FAQ**: [FAQ.md](./FAQ.md)
- **Swagger UI**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs

### Reporting Issues
- **GitHub Issues**: https://github.com/muharandy/promptsizer/issues
- **Use Templates**: See [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)

### Response Times (Beta)
- **Critical bugs**: Within 4 business hours
- **High priority**: Within 2 business days
- **Medium priority**: Within 1 week
- **Low priority**: Logged for future consideration

---

## 👥 Beta Testers

Thank you to our beta testing community!

As a beta tester, you:
- ✅ Get early access to new features
- ✅ Have direct input on API design
- ✅ Can be listed in GA release notes (optional)
- ✅ Get priority support during beta period

---

## 📜 License & Terms

### Beta Terms
- **Use**: Internal testing and development only
- **SLA**: Best-effort support during beta (no guarantees)
- **Breaking Changes**: Possible based on feedback (will be documented)
- **Data**: Pricing data updated regularly, but may have gaps

### GA Terms (Coming Soon)
- Production-ready with SLA
- Version locking (breaking changes only in major versions)
- Complete data coverage
- 24/7 support

---

## 🙏 Acknowledgments

Built by the Lakemeter team with contributions from:
- Backend engineering (API development, database design)
- Data engineering (pricing sync, data quality)
- Product management (requirements, use cases)
- Beta testers (feedback, bug reports, suggestions)

---

## 📖 Further Reading

### For Developers
1. Start with [GETTING_STARTED.md](./GETTING_STARTED.md)
2. Review [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
3. Experiment with [Swagger UI](https://lakemeter-api-335310294452632.aws.databricksapps.com/docs)
4. Check [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) for limitations

### For AI/ML Engineers
1. Read [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md)
2. Parse [OpenAPI Spec](https://lakemeter-api-335310294452632.aws.databricksapps.com/openapi.json)
3. Reference [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for context

### For Beta Testers
1. Quick start with [GETTING_STARTED.md](./GETTING_STARTED.md)
2. Follow [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)
3. Reference [FAQ.md](./FAQ.md) for common questions
4. Review [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) before reporting

### For Product/Finance Teams
1. Review [BETA_RELEASE_NOTES.md](./BETA_RELEASE_NOTES.md)
2. Explore use cases in this README
3. Try calculations in [Swagger UI](https://lakemeter-api-335310294452632.aws.databricksapps.com/docs)
4. Ask questions via [FAQ.md](./FAQ.md)

---

## 🚀 Let's Build Something Great!

We're excited to have you as part of the Lakemeter API beta program. Your feedback will help shape the future of Databricks cost management.

**Ready to get started?** → [GETTING_STARTED.md](./GETTING_STARTED.md)

**Questions?** → [FAQ.md](./FAQ.md)

**Found a bug?** → [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)

**Happy building! 🎉**

---

**Version**: 0.9.0 (Beta)  
**Last Updated**: December 18, 2024  
**Status**: Active Beta Testing

