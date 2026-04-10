---
sidebar_position: 1
slug: /
---

# Lakemeter

**Build accurate Databricks cost estimates in minutes, not days.**

Lakemeter is a web-based tool that calculates Databricks pricing across 14 workload types, 3 cloud providers, and all available regions. It turns vague "how much will this cost?" conversations into precise, exportable estimates backed by real pricing data.

## Who should use this?

### Solutions Architects and Sales Engineers

You need cost estimates for customer proposals, RFPs, or proof-of-concept planning. Lakemeter lets you configure workloads with real instance types and usage patterns, then export a professional Excel report you can hand directly to a customer.

**Start here:** [5-Minute Tutorial](/user-guide/getting-started) | [End-to-End Workflow](/user-guide/end-to-end-workflow)

### Data Engineers and Platform Teams

You need to estimate costs for a new data platform, migration, or capacity expansion. Lakemeter covers Jobs, DLT, DBSQL, and more -- so you can model your full architecture in one estimate.

**Start here:** [Quick Reference](/user-guide/quick-reference) | [Workload Guides](/user-guide/workloads)

### Administrators

You are deploying Lakemeter for your team or integrating it with other systems.

**Start here:** [Deployment Guide](/admin-guide/deployment) | [API Reference](/admin-guide/api-reference)

## What Lakemeter covers

| Category | Workload Types | What it estimates |
|----------|---------------|-------------------|
| **Compute** | Jobs, All-Purpose, DLT | DBU costs + VM infrastructure for batch, interactive, and pipeline workloads |
| **SQL Analytics** | DBSQL | Warehouse costs for Classic, Pro, and Serverless SQL |
| **AI / ML** | Model Serving, Vector Search, FMAPI (Databricks), FMAPI (Proprietary), AI Parse, Shutterstock ImageAI | Inference endpoints, vector databases, foundation model token costs, document AI, image generation |
| **Data Services** | Lakebase, Databricks Apps | Managed PostgreSQL compute and storage, hosted web applications |

**Multi-cloud:** AWS, Azure, and GCP with region-specific pricing.

**Pricing tiers:** Standard, Premium, and Enterprise -- each with different DBU rates and feature availability.

## Key capabilities

- **Real-time cost calculation** -- costs update instantly as you adjust workload parameters
- **AI Assistant** -- describe what you need in plain English and get workload configurations suggested for you
- **Excel export** -- download professional reports with full cost breakdowns, ready for customer handoff
- **Estimate sharing** -- collaborate with team members on the same estimate
- **Duplicate and compare** -- clone estimates to model alternative configurations side by side

## Quick start

1. Open Lakemeter and click **New Estimate**
2. Choose your cloud (AWS/Azure/GCP), region, and pricing tier
3. Add workloads and configure their parameters
4. Review the cost breakdown
5. Export to Excel

![Lakemeter estimates list — create and manage your cost estimates](/img/home-page.png)
*The Lakemeter home page showing your estimates with cloud provider, region, and AI assistant panel.*

Ready for the full walkthrough? See the [5-Minute Tutorial](/user-guide/getting-started).
