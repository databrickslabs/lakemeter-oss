---
sidebar_position: 1
---

# Overview

Lakemeter is a web-based cost estimation tool for the Databricks platform. It allows you to build detailed pricing estimates across all major Databricks workload types, with support for AWS, Azure, and GCP.

![Overview documentation page](/img/guides/overview-page.png)
*The Overview page — a summary of Lakemeter's capabilities, supported workloads, and cloud providers.*

![Lakemeter home page showing estimates list](/img/home-page.png)
*The Lakemeter home page — manage your estimates, filter by cloud provider, and access the AI assistant.*

![Cost summary panel — expand and collapse workload costs, hover for tooltips](/img/gifs/cost-summary.gif)
*Animated: the cost summary panel in action — expand workload costs and hover over values to see detailed breakdowns.*

## What You Can Do

### Create Estimates

Build cost estimates that include multiple workloads. Each estimate is scoped to a specific cloud provider, region, and pricing tier. You can create, duplicate, and share estimates with your team.

### Configure Workloads

Add workloads to your estimate and configure compute resources, usage patterns, and pricing options. Lakemeter supports 14 workload types covering the full Databricks platform.

### Get AI Assistance

Use the built-in AI assistant to ask pricing questions, get help configuring workloads, or generate entire estimates from natural language descriptions.

### Export Reports

Download professional Excel reports with full cost breakdowns, ready for RFP responses, procurement reviews, or internal planning.

## Supported Workload Types

| Workload | Description |
|----------|-------------|
| **Jobs** | Batch processing and ETL workflows (classic and serverless) |
| **All-Purpose** | Interactive notebooks and development clusters (classic and serverless) |
| **DLT** | Delta Live Tables for declarative data pipelines |
| **DBSQL** | Databricks SQL warehouses for analytics and BI |
| **Model Serving** | Real-time model inference endpoints |
| **Vector Search** | Vector database for similarity search |
| **FMAPI (Databricks)** | Foundation Model APIs for open-source models |
| **FMAPI (Proprietary)** | Foundation Model APIs for OpenAI, Anthropic, Google models |
| **Lakebase** | Managed PostgreSQL-compatible transactional database |
| **Databricks Apps** | Managed app hosting on Databricks |
| **AI Parse (Document AI)** | Document parsing and extraction with AI |
| **Shutterstock ImageAI** | AI image generation via Shutterstock |

Each workload type has a dedicated guide with real-world scenarios, worked cost examples, and configuration references. See [Which Workload Type Do I Need?](/user-guide/workloads) for a decision guide.

![Workloads overview page](/img/guides/workloads-overview-page.png)
*The Workloads overview — decision guide for choosing between the 14 workload types.*

## Supported Clouds and Regions

Lakemeter supports all three major cloud providers:

- **AWS** — US, EU, and AP regions
- **Azure** — All Azure regions where Databricks is available
- **GCP** — US and EU regions

Pricing is region-specific and reflects the latest Databricks pricing data.

## Pricing Tiers

Each estimate uses a pricing tier that determines DBU rates:

- **Standard** — Base pricing tier
- **Premium** — Includes advanced security and governance features
- **Enterprise** — Full platform capabilities with enhanced SLAs

## Quality Assurance

Lakemeter includes a comprehensive test suite covering AI assistant proposals, cost calculation accuracy, and Excel export verification. See the [Testing Guide](/testing/overview) for details on running and extending the test suite.
