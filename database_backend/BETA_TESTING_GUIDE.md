# 🧪 Lakemeter API - Beta Testing Guide

**Beta Version**: v0.9.0  
**Testing Period**: December 18, 2024 - January 15, 2025  
**Status**: Active Beta Testing

---

## 🎯 Beta Testing Objectives

1. **Validate Cost Accuracy** - Ensure calculations match expected values
2. **Test API Ergonomics** - Is the API easy and intuitive to use?
3. **Verify Error Handling** - Are error messages helpful and actionable?
4. **Check Documentation** - Is everything clear and complete?
5. **Assess Performance** - Is the API fast enough for real-world use?
6. **Integration Testing** - Does it work well with frontend frameworks?

---

## 🚀 Getting Started

### Prerequisites
- Databricks workspace access
- OAuth token for authentication
- API client (Postman, curl, or your frontend app)

### Step 1: Get Your OAuth Token

**From Databricks Notebook:**
```python
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
print(f"Token: {token}")
```

**From Local Terminal (if configured):**
```bash
databricks auth token --host https://your-workspace.cloud.databricks.com
```

### Step 2: Test API Connection

```bash
# Health check (no auth required)
curl https://lakemeter-api-335310294452632.aws.databricksapps.com/health

# Simple reference data (auth required)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://lakemeter-api-335310294452632.aws.databricksapps.com/api/v1/clouds
```

### Step 3: Review Documentation
- **Swagger UI**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
- **API Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **AI Agent Guide**: [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md)

---

## 📋 Testing Checklist

### Priority 1: Critical Path (Must Test) ⭐⭐⭐

#### 1. JOBS Classic Calculation
- [ ] Test with on-demand pricing (AWS/Azure/GCP)
- [ ] Test with spot workers
- [ ] Test with reserved pricing (1y/3y) on AWS
- [ ] Test with reserved pricing (1y/3y) on Azure/GCP
- [ ] Test with run-based parameters (runs_per_day, avg_runtime_minutes)
- [ ] Test with direct hours_per_month
- [ ] Verify driver cannot be spot (should error)
- [ ] Test invalid instance types (error should list alternatives)
- [ ] Test payment option validation (AWS vs Azure/GCP)

**Expected**: Costs should match known benchmarks, errors should be clear.

#### 2. DBSQL Classic/Pro Calculation
- [ ] Test with different warehouse sizes (X-Small to 4X-Large)
- [ ] Test with CLASSIC vs PRO warehouse types
- [ ] Test with multiple clusters (1-30)
- [ ] Test VM pricing tiers (on-demand, spot, reserved)
- [ ] Test with run-based vs direct hours
- [ ] Test invalid warehouse sizes (should show valid options)

**Expected**: Costs should reflect warehouse size and cluster count accurately.

#### 3. Reference Data APIs
- [ ] Get available clouds
- [ ] Get regions for each cloud (AWS/Azure/GCP)
- [ ] Get pricing tiers (verify Azure has no ENTERPRISE)
- [ ] Get instance types with filters (cloud, region, vcpu range)
- [ ] Get DBSQL warehouse sizes
- [ ] Get GPU types for Model Serving
- [ ] Get FMAPI models (Databricks + Proprietary)

**Expected**: All data returns correctly, filters work as expected.

### Priority 2: Secondary Features (Should Test) ⭐⭐

#### 4. All-Purpose Workloads
- [ ] Test All-Purpose Classic vs JOBS Classic (costs should differ)
- [ ] Test All-Purpose Serverless with performance mode
- [ ] Verify node types are required even for serverless
- [ ] Test flexible usage parameters

#### 5. Serverless Workloads
- [ ] JOBS Serverless (verify Photon always enabled)
- [ ] All-Purpose Serverless
- [ ] DBSQL Serverless (no VM costs)
- [ ] DLT Serverless (no dlt_edition parameter)
- [ ] Test serverless mode multipliers (standard vs performance)

#### 6. DLT Workloads
- [ ] DLT Classic with different editions (CORE/PRO/ADVANCED)
- [ ] DLT Serverless
- [ ] Test with Photon enabled/disabled (Classic only)

#### 7. AI/ML Workloads
- [ ] Model Serving with different GPU types
- [ ] FMAPI Databricks models (token-based and provisioned)
- [ ] FMAPI Proprietary models (OpenAI, Anthropic, Google)
- [ ] Vector Search with different modes
- [ ] Test hierarchical validation (FMAPI proprietary)

#### 8. Lakebase
- [ ] Test with different CU sizes (1, 2, 4, 8)
- [ ] Test with different node counts (1-3)
- [ ] Verify formula: DBU = CU × nodes

### Priority 3: Edge Cases (Nice to Test) ⭐

#### 9. Boundary Conditions
- [ ] Zero workers (driver-only cluster)
- [ ] Maximum workers (large cluster)
- [ ] Minimum hours per month (1 hour)
- [ ] Maximum hours per month (730+ hours)
- [ ] Very large quantities for FMAPI (billions of tokens)

#### 10. Error Handling
- [ ] Invalid cloud name
- [ ] Invalid region for cloud
- [ ] Invalid instance type
- [ ] Invalid pricing tier
- [ ] Wrong payment option for cloud
- [ ] Missing required parameters
- [ ] Conflicting parameters (run-based + direct hours)
- [ ] Invalid authentication token

#### 11. Performance Testing
- [ ] Single request latency
- [ ] Concurrent requests (5-10 simultaneous)
- [ ] Large pagination (1000+ items)
- [ ] Complex queries with all filters

---

## 📝 What to Test For

### 1. Cost Accuracy
**Compare API results with known benchmarks:**
- Do DBU costs match pricing documentation?
- Do VM costs match AWS/Azure/GCP pricing?
- Are Photon multipliers applied correctly?
- Are serverless mode multipliers correct?

**Red flags:**
- $0 costs when there should be costs
- Negative costs
- Impossibly high costs (thousands per hour)
- Costs don't scale linearly with usage

### 2. Error Message Quality
**Check that errors include:**
- Clear, human-readable message
- Error code for programmatic handling
- Field name that caused the error
- List of allowed values (when applicable)

**Red flags:**
- Generic "Internal Server Error" without details
- Stack traces exposed to users
- No guidance on how to fix the error
- Missing allowed values for validation errors

### 3. API Ergonomics
**Assess developer experience:**
- Are parameter names intuitive?
- Is the API consistent across endpoints?
- Are optional parameters clearly marked?
- Are examples in documentation accurate?
- Is the Swagger UI helpful?

**Red flags:**
- Confusing parameter names
- Inconsistent patterns between endpoints
- Required vs optional unclear
- Examples don't work

### 4. Documentation Quality
**Check that documentation:**
- Explains all parameters clearly
- Provides working examples
- Covers edge cases
- Explains cloud-specific differences
- Includes troubleshooting tips

**Red flags:**
- Missing parameter descriptions
- Examples that don't work
- No explanation of cloud differences
- No troubleshooting guidance

### 5. Performance
**Measure and record:**
- Average response time per endpoint type
- Response time under concurrent load
- Any timeout errors
- Memory or CPU spikes (if observable)

**Red flags:**
- Requests taking >5 seconds
- Timeouts under light load
- Performance degrading over time
- Inconsistent response times

---

## 🐛 How to Report Issues

### Option 1: GitHub Issues (Recommended)
Create an issue at: https://github.com/muharandy/promptsizer/issues

**Use this template:**

```markdown
## 🐛 Bug Report / 💡 Feature Request

**Type**: Bug / Feature / Documentation / Performance

**Severity**: Critical / High / Medium / Low

**Endpoint**: `/api/v1/calculate/jobs-classic`

**Description**:
Brief description of the issue or feature request.

**Steps to Reproduce**:
1. Call endpoint with parameters: `{"cloud": "AWS", ...}`
2. Observe response: `{"success": false, ...}`
3. Expected different result

**Expected Behavior**:
What you expected to happen.

**Actual Behavior**:
What actually happened.

**Request Details**:
```json
{
  "cloud": "AWS",
  "region": "us-east-1",
  ...
}
```

**Response Details**:
```json
{
  "success": false,
  "error": {...}
}
```

**Environment**:
- API Base URL: https://lakemeter-api-335310294452632.aws.databricksapps.com
- Client: Browser / Postman / Python / curl
- Timestamp: 2024-12-18 10:30:00 UTC

**Suggested Fix** (optional):
Your thoughts on how to fix it.

**Additional Context**:
Any other relevant information.
```

### Option 2: Quick Feedback Form

For minor issues or quick feedback:

```markdown
**What were you trying to do?**
[Brief description]

**What went wrong?**
[What happened]

**What should happen instead?**
[Expected behavior]

**Endpoint**: [Which API endpoint]

**Severity**: [How urgent is this?]
```

---

## 📊 Feedback Categories

### 1. Critical Bugs 🔴
**Report immediately if you find:**
- Incorrect cost calculations (off by >5%)
- Security vulnerabilities
- Data corruption or loss
- Complete API unavailability
- Authentication failures

**Expected Response**: Within 4 business hours

### 2. High Priority Issues 🟠
**Report soon if you find:**
- Confusing error messages
- Missing validation
- Performance problems (>3 second response times)
- Missing critical documentation

**Expected Response**: Within 2 business days

### 3. Medium Priority Issues 🟡
**Report when convenient:**
- Minor inconsistencies
- Documentation improvements
- UI/UX suggestions for Swagger
- Feature requests for GA release

**Expected Response**: Within 1 week

### 4. Low Priority Issues 🟢
**Nice to have:**
- Documentation typos
- Example improvements
- Code organization suggestions
- Future enhancement ideas

**Expected Response**: Logged for future consideration

---

## ✅ Success Criteria

Your beta testing is successful when you've:
- [ ] Tested at least 5 different calculation endpoints
- [ ] Tested both success and error scenarios
- [ ] Provided feedback on at least 3 aspects (accuracy, errors, docs, etc.)
- [ ] Reported any critical or high-priority issues found
- [ ] Confirmed or refuted cost accuracy for your use cases

---

## 🎁 Beta Tester Recognition

As a beta tester, you'll:
- Get early access to new features
- Have direct input on API design decisions
- Be listed in release notes (if you want)
- Get priority support during beta period

---

## 📅 Beta Timeline

### Week 1-2: Initial Testing (Dec 18 - Dec 31)
- Focus: Core calculation endpoints
- Goal: Find critical bugs and accuracy issues

### Week 3: Integration Testing (Jan 1 - Jan 7)
- Focus: Frontend integration
- Goal: Validate API ergonomics and documentation

### Week 4: Performance & Polish (Jan 8 - Jan 15)
- Focus: Load testing and refinement
- Goal: Optimize and finalize for GA

### Post-Beta: GA Preparation (Jan 16+)
- Incorporate all feedback
- Fix all critical/high priority issues
- Prepare for production release

---

## 📞 Support During Beta

### Documentation Resources
- **API Reference**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **AI Agent Guide**: [AI_AGENT_GUIDE.md](./AI_AGENT_GUIDE.md)
- **Swagger UI**: https://lakemeter-api-335310294452632.aws.databricksapps.com/docs
- **Known Issues**: [KNOWN_ISSUES.md](./KNOWN_ISSUES.md)

### Getting Help
1. **Check documentation first** - Most questions are answered there
2. **Try Swagger UI** - Interactive testing and examples
3. **Search existing issues** - Someone may have already reported it
4. **Create new issue** - Use the templates above

### Beta Testing Tips
- ✅ Test incrementally (start simple, add complexity)
- ✅ Document your findings as you go
- ✅ Compare results with known benchmarks
- ✅ Test both happy path and error cases
- ✅ Try unexpected inputs
- ✅ Think like an end user

---

## 🙏 Thank You!

Your participation in the beta program is invaluable. Every bug report, feature suggestion, and documentation improvement helps make Lakemeter API better for everyone.

**Questions about beta testing?**
- Review this guide thoroughly first
- Check [BETA_RELEASE_NOTES.md](./BETA_RELEASE_NOTES.md) for context
- Create an issue if still unclear

**Happy Testing! 🚀**

