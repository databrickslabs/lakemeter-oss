# 🚀 Lakemeter API - Beta Release v0.9.0

**Release Date**: December 18, 2024  
**Status**: Beta (Internal Testing)  
**API Base URL**: `https://lakemeter-api-335310294452632.aws.databricksapps.com`

---

## 🎯 Overview

The Lakemeter API provides comprehensive cost calculation and reference data for Databricks workloads across AWS, Azure, and GCP. This beta release includes all core functionality and is ready for internal testing and integration.

---

## ✨ What's Included

### Cost Calculation Endpoints (13 endpoints)
- ✅ **JOBS Classic** - Classic JOBS with VM costs
- ✅ **JOBS Serverless** - Serverless JOBS (DBU only)
- ✅ **All-Purpose Classic** - Interactive clusters with VM costs
- ✅ **All-Purpose Serverless** - Serverless interactive workloads
- ✅ **DBSQL Classic/Pro** - SQL warehouses with VM costs
- ✅ **DBSQL Serverless** - Serverless SQL warehouses
- ✅ **DLT Classic** - Delta Live Tables with VM costs
- ✅ **DLT Serverless** - Serverless Delta Live Tables
- ✅ **Model Serving** - GPU-based model serving
- ✅ **FMAPI Databricks** - Databricks-hosted models
- ✅ **FMAPI Proprietary** - OpenAI, Anthropic, Google models
- ✅ **Vector Search** - Vector database search
- ✅ **Lakebase** - Managed PostgreSQL

### Reference Data Endpoints (30+ endpoints)
- ✅ **Geography** - Clouds, regions, pricing tiers
- ✅ **Salesforce** - Accounts, opportunities, use cases
- ✅ **Compute** - Instance types, families, VM pricing options
- ✅ **DBSQL** - Warehouse types, sizes, hardware specs
- ✅ **Model Serving** - GPU types and DBU rates
- ✅ **FMAPI** - Available models (Databricks & proprietary)
- ✅ **Vector Search** - Available modes
- ✅ **Lakebase** - CU sizes
- ✅ **Photon** - Multipliers by SKU type
- ✅ **Serverless** - Mode multipliers
- ✅ **DBU Pricing** - Base rates by cloud/region/tier

### Key Features
- ✅ **Cloud-Aware Validation** - Different rules for AWS vs Azure vs GCP
- ✅ **Flexible Usage Parameters** - Accept run-based or direct hours
- ✅ **Comprehensive Error Messages** - Include allowed values for easy debugging
- ✅ **Pagination Support** - For large datasets (instance types, Salesforce data)
- ✅ **OpenAPI/Swagger** - Auto-generated interactive documentation
- ✅ **OAuth Authentication** - Secure Databricks user authentication
- ✅ **AI Agent Ready** - Machine-readable OpenAPI spec for AI consumption

---

## 🎨 What's Unique

### 1. **Cloud-Specific Business Logic**
- AWS reserved pricing requires payment options (no_upfront, partial_upfront, all_upfront)
- Azure/GCP reserved pricing uses simplified "NA" payment option
- Azure doesn't support ENTERPRISE tier (validated dynamically)

### 2. **Smart Validation**
- Driver nodes cannot be spot instances (stability requirement)
- Instance type validation includes available alternatives in error messages
- Hierarchical validation for FMAPI proprietary models

### 3. **Flexible Usage Calculation**
Most endpoints accept EITHER:
- **Run-based**: `runs_per_day` + `avg_runtime_minutes` + `days_per_month`
- **Direct hours**: `hours_per_month`

### 4. **Serverless-Aware**
- Photon is always enabled for serverless (not a parameter)
- No VM costs for serverless (DBU only)
- Still requires node types (for DBU calculation)

---

## 📊 Beta Test Coverage

### ✅ Verified Working
- All 13 calculation endpoints return correct costs
- All reference data endpoints return valid data
- Cloud-specific payment option validation
- Instance type validation with error messages
- FMAPI hierarchical validation
- DBSQL warehouse size validation (Classic/Pro vs Serverless)
- Flexible usage parameters (run-based vs direct hours)
- Error handling with detailed JSON responses

### 🧪 Needs Beta Testing
- **Performance under load** - Concurrent requests
- **Edge cases** - Unusual parameter combinations
- **Frontend integration** - Real-world UI workflows
- **Error message clarity** - Are they helpful enough?
- **Documentation completeness** - What's missing?
- **API ergonomics** - Is the API intuitive to use?

---

## 🔧 Technical Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (Databricks Lakebase)
- **Authentication**: Databricks OAuth (user tokens)
- **Deployment**: Databricks Apps
- **Documentation**: OpenAPI 3.0 (auto-generated)
- **Validation**: Custom modular validators with cloud awareness

---

## 📝 Known Limitations

### Data Quality
- ✅ **FIXED**: Azure reserved VM pricing (was 8760x too high, now corrected)
- ⚠️ **Minor**: Some GCP instance types may have incomplete pricing data
- ⚠️ **Minor**: FMAPI proprietary model list may lag behind provider updates

### API Functionality
- ⚠️ **No rate limiting** - Could be overwhelmed by excessive requests
- ⚠️ **No caching** - Every request hits the database
- ⚠️ **No batch endpoints** - Must calculate one workload at a time
- ⚠️ **No cost comparison** - Can't compare multiple configurations in one call

### Documentation
- ✅ Complete API reference documentation
- ✅ AI agent integration guide
- ⚠️ **Need**: Video walkthrough
- ⚠️ **Need**: Frontend integration examples (React/Vue/Angular)
- ⚠️ **Need**: Postman collection

---

## 🚨 Breaking Changes (None in Beta)

This is the initial beta release, so no breaking changes yet. However, be aware:

- **API structure may change** based on beta feedback
- **Error codes may be refined** for consistency
- **Response format may be enhanced** with additional metadata
- **Validation rules may be adjusted** based on real-world usage

We will document all breaking changes clearly before GA release.

---

## 🎯 Beta Success Criteria

We'll consider the beta successful when:

1. ✅ **All endpoints return correct costs** (verified)
2. ⏳ **Frontend successfully integrates** (pending)
3. ⏳ **No critical bugs found** during testing
4. ⏳ **Performance is acceptable** under realistic load
5. ⏳ **Documentation is clear** and complete
6. ⏳ **Error messages are helpful** for developers
7. ⏳ **Beta testers report positive experience**

---

## 📅 Roadmap to GA

### Phase 1: Beta Testing (Current)
- Internal testing by frontend/backend teams
- Integration testing with UI
- Performance testing under load
- Documentation refinement

### Phase 2: Beta Feedback (2 weeks)
- Collect and prioritize feedback
- Fix critical bugs
- Enhance error messages
- Add missing documentation

### Phase 3: Release Candidate (1 week)
- Final bug fixes
- Performance optimization
- Add rate limiting
- Add caching for reference data

### Phase 4: GA Release (TBD)
- Production deployment
- Version locking (v1.0.0)
- SLA commitment
- Support process

---

## 🔗 Quick Links

- **Swagger UI**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
- **OpenAPI Spec**: https://lakemeter-api-335310294452632.aws.databricksapps.com/openapi.json
- **API Documentation**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **AI Agent Guide**: [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md)
- **GitHub Repository**: https://github.com/muharandy/promptsizer/tree/database_backend/database_backend
- **Beta Testing Guide**: [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)
- **Known Issues**: [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)

---

## 👥 Beta Program

### Who Should Test?
- ✅ Frontend developers integrating the API
- ✅ Backend developers verifying calculations
- ✅ Product managers validating use cases
- ✅ Data analysts checking cost accuracy

### How to Report Issues
See [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md) for:
- How to test specific features
- Issue reporting template
- Feedback channels
- Expected response times

---

## 🙏 Thank You!

Thank you for participating in the Lakemeter API beta program. Your feedback will help us build a better product for everyone.

**Questions or issues?** Contact the API team:
- GitHub Issues: [Create an issue](https://github.com/muharandy/promptsizer/issues)
- Documentation: Review docs and FAQs first
- Direct feedback: Use the beta testing guide templates

---

## 📜 Changelog

### v0.9.0 (Beta) - December 18, 2024

**Added:**
- Initial release with 13 calculation endpoints
- 30+ reference data endpoints
- Comprehensive validation system
- Cloud-aware business logic
- Flexible usage parameters
- OpenAPI/Swagger documentation
- AI agent integration support

**Fixed:**
- Azure reserved VM pricing (divided by hours in term)
- FMAPI endpoints returning $0 costs
- DBSQL Serverless warehouse size validation
- Payment option validation for AWS reserved pricing

**Known Issues:**
- No rate limiting (could be overwhelmed by excessive requests)
- No caching (every request hits database)
- Minor incomplete pricing data for some GCP instance types

