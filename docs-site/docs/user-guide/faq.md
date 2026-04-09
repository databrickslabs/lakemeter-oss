---
sidebar_position: 10
---

# Frequently Asked Questions

![FAQ documentation page](/img/guides/faq-guide.png)
*The FAQ page — answers to the most common questions about Lakemeter, organized by topic.*

![Workload decision table](/img/guides/faq-workload-table.png)
*Quick reference table for choosing the right workload type.*

## General

### What is Lakemeter?

Lakemeter is a cost estimation tool for the Databricks platform. It lets you model workloads across 12 Databricks product types (Jobs, DBSQL, DLT, Model Serving, Vector Search, FMAPI, Lakebase, Databricks Apps, AI Parse, Shutterstock ImageAI, and more), calculate monthly and annual costs based on real Databricks pricing data, and export professional Excel reports for procurement or planning.

### How accurate are the cost estimates?

Lakemeter uses DBU rates and instance pricing pulled directly from Databricks reference tables. The calculations match the formulas Databricks uses for billing. However, actual costs may differ due to committed-use discounts, spot pricing fluctuations, auto-scaling behavior, and usage patterns that deviate from your modeled assumptions. Always verify critical estimates against the [official Databricks pricing page](https://www.databricks.com/product/pricing).

### Is Lakemeter an official Databricks product?

No. Lakemeter is an internal field engineering tool built on Databricks Apps. It is not an officially supported Databricks product.

## Configuration

### What do Cloud, Region, and Tier mean?

- **Cloud** — The cloud provider (AWS, Azure, or GCP). Each has different instance types and VM pricing.
- **Region** — The cloud region (e.g., `us-east-1`). DBU rates can vary by region for some SKUs.
- **Tier** — The Databricks pricing tier: **Standard**, **Premium**, or **Enterprise**. Standard tier only supports Classic compute workloads. Premium and Enterprise unlock Serverless, SQL Pro, Vector Search, FMAPI, and other advanced features.

See the [Getting Started](./getting-started) guide for how to set these when creating an estimate.

### Which workload type should I choose?

| If you're estimating... | Use this workload type |
|------------------------|----------------------|
| Batch ETL, scheduled Spark jobs | [Jobs Compute](./jobs-compute) |
| Interactive notebooks, development clusters | [All-Purpose Compute](./all-purpose-compute) |
| Streaming or declarative ETL pipelines | [DLT Pipelines](./dlt-pipelines) |
| BI dashboards, ad-hoc SQL queries | [DBSQL Warehouses](./dbsql-warehouses) |
| Real-time ML inference with GPUs | [Model Serving](./model-serving) |
| Similarity search, embeddings storage | [Vector Search](./vector-search) |
| LLM inference (Llama, DBRX, etc.) | [FMAPI — Databricks](./fmapi-databricks) |
| LLM inference (Claude, GPT, Gemini) | [FMAPI — Proprietary](./fmapi-proprietary) |
| Managed PostgreSQL database | [Lakebase](./lakebase) |
| Hosting a web app on Databricks | Databricks Apps |
| Parsing documents with AI | AI Parse (Document AI) |
| Generating images with AI | Shutterstock ImageAI |

### What's the difference between Classic and Serverless?

**Classic** compute means you specify the exact instance types (e.g., `i3.xlarge`) and pay for both DBU consumption and VM infrastructure separately. You have full control over cluster configuration.

**Serverless** compute means Databricks manages the infrastructure. You pay only for DBUs at a higher per-DBU rate, but there are no separate VM costs and no cluster startup time. Whether Serverless is cheaper depends on the workload — it excels for burst or low-utilization patterns, but sustained high-utilization workloads may cost less on Classic. See the [Classic vs Serverless comparison](./calculation-reference#worked-example-4-classic-vs-serverless-comparison) for a detailed cost breakdown.

## AI Assistant

### What can the AI assistant do?

The assistant can create fully configured workloads from a natural language description, analyze your existing estimate for cost optimization opportunities, suggest complete multi-workload architectures for common patterns (like RAG chatbots), and answer general Databricks pricing questions. See the [AI Assistant guide](./ai-assistant) for conversation examples.

### Can the AI assistant modify my existing workloads?

The assistant can propose **new** workloads and can analyze your existing ones, but it cannot directly edit workloads you've already created. To modify an existing workload, use the workload form in the UI.

## Export & Pricing

### What format does the export use?

Lakemeter exports to `.xlsx` (Excel) format. The file includes formula-based cells, color-coded headers, frozen panes, and a cost summary section. You can open it in Excel, Google Sheets, or any spreadsheet application. See the [Exporting guide](./exporting) for full details.

### Can I apply my negotiated discount?

Yes. Each workload row in the Excel export has a **Discount %** column. Enter your negotiated discount rate and all cost cells recalculate automatically using Excel formulas. You can also set different discounts per workload.

### Why do some workloads show two rows in the export?

**Lakebase** and **Vector Search** can produce two rows — one for compute costs (DBU-based) and one for storage costs (direct dollar amount). Both rows are included in the totals. See the [Exporting guide](./exporting#3-multi-row-workloads) for details.

### How are DBU rates determined?

Lakemeter uses DBU rates from Databricks reference pricing tables, loaded at deployment time. The rate depends on three factors: the **SKU** (product type, like `JOBS_COMPUTE` or `SERVERLESS_SQL_COMPUTE`), the **cloud region**, and the **pricing tier**. See the [Calculation Reference](./calculation-reference) for the exact formulas and rate tables.

## Troubleshooting

### A workload type is grayed out — why?

Some workload types are only available on **Premium** or **Enterprise** tiers. If you selected the Standard tier for your estimate, workloads like DBSQL Serverless, Vector Search, FMAPI, Model Serving, Databricks Apps, AI Parse, and Shutterstock ImageAI will be disabled. Change your estimate's tier to Premium or Enterprise to unlock them.

### The cost seems too high or too low — what should I check?

Common things to verify:
1. **Hours/Month** — 730 means 24/7 operation. For business-hours-only usage, ~176 hours (8 hrs × 22 days) is more realistic.
2. **Number of workers** — Each worker multiplies both DBU and VM costs.
3. **Photon** — Increases the DBU rate by a multiplier that depends on the workload type and cloud provider (2.9x for Jobs/DLT on AWS, 2.5x on Azure/GCP, 2.0x for All-Purpose). Make sure it's enabled only if you plan to use it.
4. **Serverless vs Classic** — Serverless has no VM costs but higher DBU rates. Classic has both.
5. **Discount** — The export shows list prices by default. Apply your discount in the Excel file.
