---
sidebar_position: 10
---

# Frequently Asked Questions

## General

### What is Lakemeter?

Lakemeter is a sizing and cost-estimation tool for supported Databricks workloads. It turns usage assumptions into monthly and annual planning costs and exports the supporting calculations to Excel.

### How should I interpret the cost estimates?

Lakemeter uses its loaded pricing data and the assumptions entered in each workload form. The results are planning-grade estimates, not billing guarantees. Actual costs may differ because of commercial terms and usage that does not match the modeled scenario. Verify important assumptions against the [official Databricks documentation](https://docs.databricks.com/), the [Databricks pricing page](https://www.databricks.com/product/pricing), and customer-specific terms.

### Is Lakemeter an official Databricks product?

No. Lakemeter is an open-source Databricks Labs project built as a Databricks App. It is not an officially supported Databricks product.

## Configuration

### What do Cloud, Region, and Tier mean?

- **Cloud** identifies the selected deployment provider.
- **Region** identifies the pricing region used for rate lookup.
- **Tier** identifies the pricing tier used for SKU availability and rate lookup.

The options shown in Lakemeter determine what can be selected for an estimate. See [Getting Started](./getting-started) for the workflow and use the official Databricks documentation for current platform availability.

### Which workload type should I choose?

Use the [Workload Sizing Guides](./workloads). The catalog maps each sizing need to its canonical Lakemeter guide, including Databricks Apps, AI Parse, and Shutterstock ImageAI.

### What's the difference between Classic and Serverless?

For a **Classic** calculation, Lakemeter asks for instance and scale-out assumptions and models DBU and VM costs separately.

For a **Serverless** calculation, Lakemeter does not add a separate VM component. Compare the expanded calculations using the usage assumptions appropriate for each mode. See the [Calculation Reference](./calculation-reference) for the shared cost structure and the official Databricks documentation for current product behavior.

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

### Why do some workloads show multiple rows in the export?

Some workloads contain separately priced components. Vector Search can add a storage row. Lakebase can include compute, storage, PITR, and snapshot rows when those quantities are configured. All emitted rows are included in the totals. See the [Exporting guide](./exporting#3-multi-row-workloads).

### How are DBU rates determined?

Lakemeter resolves the list rate for the selected SKU and estimate context from its loaded pricing data. Use the [SKU Explorer](./pricing/sku-explorer) to inspect available rates and the [Calculation Reference](./calculation-reference) to understand how a rate is applied. Verify current public pricing on the [Databricks pricing page](https://www.databricks.com/product/pricing).

## Troubleshooting

### A workload type is grayed out — why?

Lakemeter only enables workload options compatible with the selected estimate context. If a workload is unavailable, review the cloud, region, and tier selections. Use the official Databricks documentation to confirm current product availability.

### The cost seems too high or too low — what should I check?

Common things to verify:
1. **Hours/Month** — 730 means 24/7 operation. For business-hours-only usage, ~176 hours (8 hrs × 22 days) is more realistic.
2. **Number of workers** — Each worker multiplies both DBU and VM costs.
3. **Acceleration and mode options** — Enable them only when they match the planned workload, then inspect the resulting DBU quantity.
4. **Serverless vs Classic** — Serverless has no VM costs but higher DBU rates. Classic has both.
5. **Discount** — The export shows list prices by default. Apply your discount in the Excel file.
