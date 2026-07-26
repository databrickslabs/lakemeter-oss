# Article 2 Outline: Create Your First Databricks Cost Estimate with Lakemeter in 5 Minutes

## Working Title

Create Your First Databricks Cost Estimate with Lakemeter in 5 Minutes

## Article Goal

Turn the existing 5-minute tutorial into a customer-facing Medium article that helps readers understand how quickly they can get value from Lakemeter.

Primary call to action:

- Try the 5-minute tutorial.
- Star the GitHub repo if useful.
- Use Lakemeter for early Databricks workload planning conversations.

## Target Reader

Customers, partners, and field teams who want a quick, practical walkthrough before deciding whether to deploy Lakemeter.

## Suggested Opening

Cost estimation becomes much easier when the workflow is structured.

In this walkthrough, we will use Lakemeter to create a Databricks cost estimate for a simple data platform with two workloads: a nightly ETL pipeline and a serverless analytics warehouse.

By the end, we will have a shareable estimate that can be exported to Excel and used in a planning conversation.

## Structure

### 1. What We Are Building

Use the same scenario from the docs:

- Cloud: AWS
- Region: us-east-1
- Tier: Premium
- Workload 1: Jobs Classic ETL pipeline
- Workload 2: DBSQL Serverless analytics warehouse

Explain why this is a useful starter scenario:

- Covers classic compute and serverless SQL.
- Shows both infrastructure and DBU-style pricing.
- Produces a realistic multi-workload estimate.

### 2. Step 1: Create an Estimate

Walk through:

- Open Lakemeter.
- Click New Estimate.
- Enter `Q4 Data Platform - AWS`.
- Select AWS, us-east-1, Premium.
- Create the estimate.

Suggested asset:

- `assets/lakemeter-calculator-page.png` or manual screenshot of new estimate flow.

### 3. Step 2: Add a Jobs Workload

Use the tutorial configuration:

- Workload name: `ETL Pipeline`
- Workload type: Jobs
- Classic compute
- Driver: `m5d.xlarge`
- Worker: `m5d.xlarge`
- Workers: 4
- Runs per day: 2
- Runtime: 45 minutes
- Days per month: 30

Explain the calculation:

- 2 runs/day x 45 minutes = 1.5 hours/day.
- 30 days = 45 compute-hours/month.
- Lakemeter calculates DBU and VM cost based on selected node types and pricing assumptions.

Suggested asset:

- Workload form screenshot.
- Expanded cost breakdown screenshot.

### 4. Step 3: Add a DBSQL Serverless Workload

Use the tutorial configuration:

- Workload name: `Analytics Warehouse`
- Workload type: DBSQL
- Serverless enabled
- Size: Small
- Clusters: 1
- Hours per month: 220

Explain the calculation:

- Small DBSQL Serverless warehouse consumes 12 DBU/hour.
- 220 hours/month = 2,640 DBUs/month.
- No separate VM cost because serverless infrastructure is included in the DBU rate.

### 5. Step 4: Review the Estimate

Highlight:

- Workload-level cost cards.
- Total monthly estimate.
- DBU breakdown.
- Expandable formulas and assumptions.

Positioning:

- The value is not just the final number.
- The value is that assumptions are visible and easy to discuss.

Suggested asset:

- `assets/lakemeter-cost-breakdown.png`.

### 6. Step 5: Export to Excel

Explain:

- Export creates a shareable artifact.
- Useful for RFPs, planning meetings, budgeting discussions, or handoff to customer teams.
- Includes workload table, SKU details, assumptions, and totals.

Suggested asset:

- `assets/lakemeter-excel-export.png`.

### 7. What to Try Next

Suggested next steps:

- Add Lakebase for an application backend.
- Add Model Serving or FMAPI for AI workloads.
- Use AI Assistant to describe a workload in natural language.
- Duplicate the estimate and compare regions or tiers.

## Links to Include

- GitHub: https://github.com/databrickslabs/lakemeter-oss
- 5-minute tutorial: https://databrickslabs.github.io/lakemeter-oss/user-guide/getting-started
- Release: https://github.com/databrickslabs/lakemeter-oss/releases/tag/v0.1.0

## Draft LinkedIn Teaser for Article 2

Want to see Lakemeter in action?

I put together a quick walkthrough showing how to create a Databricks cost estimate with two workloads: a Jobs ETL pipeline and a DBSQL Serverless warehouse.

In a few minutes, you can create an estimate, review workload-level cost assumptions, and export a shareable Excel file for planning conversations.

Tutorial: https://databrickslabs.github.io/lakemeter-oss/user-guide/getting-started

GitHub: https://github.com/databrickslabs/lakemeter-oss

If you find it useful, please star the repo and share feedback.

