# 📊 Lakemeter API - Beta Test Spreadsheet Template

Create a Google Sheet or Excel file with these 4 tabs:

---

## Sheet 1: Test Checklist

**Purpose**: Track what endpoints you've tested

| Endpoint | Tested? | Works? | Issues Found | Comments |
|----------|---------|--------|--------------|----------|
| **JOBS** |
| `/api/v1/calculate/jobs-classic` | ☐ | ☐ | | |
| `/api/v1/calculate/jobs-serverless` | ☐ | ☐ | | |
| **All-Purpose** |
| `/api/v1/calculate/all-purpose-classic` | ☐ | ☐ | | |
| `/api/v1/calculate/all-purpose-serverless` | ☐ | ☐ | | |
| **DBSQL** |
| `/api/v1/calculate/dbsql-classic-pro` | ☐ | ☐ | | |
| `/api/v1/calculate/dbsql-serverless` | ☐ | ☐ | | |
| **DLT** |
| `/api/v1/calculate/dlt-classic` | ☐ | ☐ | | |
| `/api/v1/calculate/dlt-serverless` | ☐ | ☐ | | |
| **AI/ML** |
| `/api/v1/calculate/model-serving` | ☐ | ☐ | | |
| `/api/v1/calculate/fmapi-databricks` | ☐ | ☐ | | |
| `/api/v1/calculate/fmapi-proprietary` | ☐ | ☐ | | |
| `/api/v1/calculate/vector-search` | ☐ | ☐ | | |
| `/api/v1/calculate/lakebase` | ☐ | ☐ | | |
| **Reference Data** |
| `/api/v1/clouds` | ☐ | ☐ | | |
| `/api/v1/regions` | ☐ | ☐ | | |
| `/api/v1/instances/types` | ☐ | ☐ | | |
| `/api/v1/dbsql/warehouse-sizes` | ☐ | ☐ | | |

**Instructions:**
- Check "Tested?" when you've tried the endpoint
- Check "Works?" if it returns correct results
- Note any issues in "Issues Found" column
- Add any comments or questions

---

## Sheet 2: Bug Reports

**Purpose**: Track bugs you find

| Date | Tester Name | Endpoint | Severity | Description | Expected | Actual | Status |
|------|-------------|----------|----------|-------------|----------|--------|--------|
| 2024-12-18 | John | /calculate/jobs-classic | High | Returns $0 cost | $500/month | $0 | Open |
| | | | | | | | |

**Severity Levels:**
- **Critical**: API down, security issue, completely wrong calculations
- **High**: Important feature broken, confusing errors, bad calculations (>10% off)
- **Medium**: Minor issues, unclear documentation, missing validations
- **Low**: Typos, nice-to-haves, suggestions

---

## Sheet 3: Cost Validation

**Purpose**: Compare API costs with your known costs

| Workload Type | Cloud | Region | Config Summary | API Cost ($/month) | Actual Cost ($/month) | Difference | Match? | Notes |
|---------------|-------|--------|----------------|-------------------|---------------------|------------|--------|-------|
| JOBS Classic | AWS | us-east-1 | m5.xlarge, 10 workers, 160h | $821.52 | $850.00 | -3.3% | ✓ | Close enough |
| DBSQL Serverless | AZURE | eastus | Medium, 730h | | | | | Need to test |
| | | | | | | | | |

**Instructions:**
- Test with your real workload configurations if possible
- Compare API results with actual Databricks bills
- Flag any differences >5% as potential issues
- Note: Small differences (<5%) are normal due to rounding

---

## Sheet 4: General Feedback

**Purpose**: Share your thoughts and suggestions

| Date | Tester Name | Category | Rating (1-5) | Feedback | Suggestion |
|------|-------------|----------|--------------|----------|------------|
| 2024-12-18 | Jane | Documentation | 4 | Clear and helpful | Add more examples for FMAPI |
| | | Error Messages | 5 | Very helpful! | - |
| | | Performance | 3 | A bit slow | Add caching |

**Categories to rate:**
- **API Usability** - Is it easy to use?
- **Documentation** - Is it clear and complete?
- **Error Messages** - Are they helpful?
- **Performance** - Is it fast enough?
- **Swagger UI** - Is the interactive docs useful?

**Rating Scale:**
- 5 = Excellent
- 4 = Good
- 3 = OK (needs improvement)
- 2 = Poor
- 1 = Very Poor

---

## How to Use This Template

### Option 1: Google Sheets (Recommended for Teams)
1. Create a new Google Sheet
2. Create 4 tabs: "Test Checklist", "Bug Reports", "Cost Validation", "General Feedback"
3. Copy the tables above into each tab
4. Share with your team (edit access)
5. Everyone can fill in their results
6. Export to Excel or CSV when done

### Option 2: Excel (Individual Testing)
1. Create a new Excel file
2. Create 4 sheets as above
3. Fill in as you test
4. Email the file back to the API team

### Option 3: CSV Files (Simple)
1. Create 4 CSV files (one per sheet)
2. Import into your preferred tool
3. Share via email or GitHub

---

## Tips for Beta Testers

### 1. Start Simple
- Test 3-5 endpoints first
- Focus on the workload types you use most
- Don't try to test everything at once

### 2. Compare with Reality
- Use your actual workload configs if possible
- Compare API results with Databricks bills
- Flag anything that looks wrong

### 3. Be Specific in Comments
**Good**: "JOBS Classic with spot workers returns $0 VM cost when using payment_option='no_upfront'"  
**Less helpful**: "Doesn't work"

### 4. Include Request Details
When reporting bugs, include:
- Endpoint URL
- Request body (JSON)
- Response received
- What you expected

### 5. Test Both Success and Errors
- Try valid configurations (should work)
- Try invalid inputs (should give clear errors)
- Check if error messages are helpful

---

## Submitting Your Results

### When You're Done Testing:

1. **Export your spreadsheet** as:
   - Google Sheets: File → Download → Excel (.xlsx)
   - Or share the Google Sheet link

2. **Email to**: API team or upload to shared drive

3. **Or create GitHub issues** for any bugs found:
   - Go to: https://github.com/muharandy/promptsizer/issues
   - Use your spreadsheet notes to create detailed issues

---

## Example: Filled Test Checklist

| Endpoint | Tested? | Works? | Issues Found | Comments |
|----------|---------|--------|--------------|----------|
| `/api/v1/calculate/jobs-classic` | ✓ | ✓ | None | Works great! Cost matches our prod cluster |
| `/api/v1/calculate/jobs-serverless` | ✓ | ✗ | Returns $0 | See bug report #1 |
| `/api/v1/calculate/dbsql-serverless` | ✓ | ✓ | Error message unclear | Works but error message could be better |

---

## Example: Filled Bug Report

| Date | Tester Name | Endpoint | Severity | Description | Expected | Actual | Status |
|------|-------------|----------|----------|-------------|----------|--------|--------|
| 2024-12-18 | John | /calculate/jobs-serverless | High | Returns $0 DBU cost | ~$500/month | $0 | Open |

**Full Details:**
```json
Request: {
  "cloud": "AWS",
  "region": "us-east-1",
  "tier": "PREMIUM",
  "driver_node_type": "m5.xlarge",
  "worker_node_type": "m5.xlarge",
  "num_workers": 10,
  "serverless_mode": "standard",
  "hours_per_month": 160
}

Response: {
  "success": true,
  "data": {
    "total_cost": {"cost_per_month": 0}
  }
}
```

---

## Questions?

- **Documentation**: Check [GETTING_STARTED.md](./GETTING_STARTED.md) and [FAQ.md](./FAQ.md)
- **How to test**: See [BETA_TESTING_GUIDE.md](./BETA_TESTING_GUIDE.md)
- **Known issues**: Check [KNOWN_ISSUES.md](./KNOWN_ISSUES.md) first

**Need help?** Create a GitHub issue or contact the API team.

---

**Template Version**: 1.0  
**Last Updated**: December 18, 2024

