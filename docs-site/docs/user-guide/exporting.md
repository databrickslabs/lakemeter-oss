---
sidebar_position: 6
---

# Exporting to Excel

Lakemeter exports your estimates to professionally formatted Excel spreadsheets — ready for RFP responses, procurement reviews, internal planning, or vendor comparisons.

![Export guide documentation page](/img/guides/export-guide.png)
*The Export guide — single and bulk export workflows with file naming conventions.*

![Excel spreadsheet structure](/img/guides/export-excel-structure.png)
*Detailed breakdown of the Excel export: header, workload table, cost summary, legend, and assumptions.*

![Exporting an estimate to Excel — click Export, download completes](/img/gifs/export-excel.gif)
*Animated: exporting an estimate — click the Export button and the Excel file downloads automatically.*

## How to Export

### Single Estimate

1. Open the estimate you want to export
2. Click the **Export** button (download arrow icon) in the top bar
3. An `.xlsx` file downloads automatically

**File name format:** `Databricks_Estimate_{estimate_name}_{YYYYMMDD}.xlsx`

### Bulk Export (All Estimates)

From the Estimates list page, click the **Export All** button to download a summary spreadsheet containing all your estimates in one file. This creates an "All Estimates" sheet with each estimate's name, cloud, region, tier, status, and dates.

## What's in the Excel File

The exported spreadsheet contains a single sheet called "Databricks Estimate" with several sections:

### 1. Header

The top rows display your estimate metadata:
- Estimate name, cloud provider, region, and pricing tier
- Status and version number
- Created and last-updated dates

### 2. Workloads Table (30 Columns)

Each workload in your estimate becomes one row (or two rows for workloads with separate storage costs). The columns are grouped by purpose:

| Group | Columns | What's there |
|-------|---------|-------------|
| **Identity** | Workload Name, Type, Mode, Configuration, SKU | What this workload is and how it's configured |
| **VM Configuration** | Driver Instance, Worker Instance, # Workers, Pricing Tiers | Instance types and cluster shape (Classic only) |
| **Usage** | Hours/Month | How much this workload runs — calculated from runs/day or entered directly |
| **Token Configuration** | Rate Type, Tokens/Month (M), DBU per 1M Tokens | For FMAPI workloads: token volumes and rates |
| **DBU Costs** | DBU/Hour, Monthly DBUs, List Rate, Discount %, Discounted Rate, List Cost, Discounted Cost | The core Databricks billing — all formula-based |
| **VM Costs** | Driver $/hr, Worker $/hr, Driver VM Cost, Worker VM Cost, Total VM Cost | Infrastructure costs for Classic compute (zero for Serverless) |
| **Totals** | Total Cost (List), Total Cost (Discounted) | Combined DBU + VM costs at list and discounted rates |
| **Notes** | Notes | Workload-specific details (e.g., "Photon enabled", "Storage Optimized") |

:::info Key Detail
All cost cells use **Excel formulas**, not static values. If you change an input (like discount percentage), the costs recalculate automatically in Excel.
:::

### 3. Multi-Row Workloads

Two workload types produce **two rows** in the export:

- **Lakebase** — Row 1: compute costs (DBU-based), Row 2: storage costs (DSU-based, direct dollar amount)
- **Vector Search** — Row 1: compute costs, Row 2: storage costs (if storage GB > 0)

The totals row at the bottom uses `SUM` formulas that include both compute and storage sub-rows.

### 4. Cost Summary

Below the workloads table, a summary section shows:
- Monthly and annual totals for DBU costs, VM costs, and combined total
- Totals at both list price and discounted price

### 5. Legend

A color-coded legend explaining the column groups:
- **Blue** — DBU-related costs (Databricks compute units)
- **Cyan** — Token-based pricing (FMAPI workloads)
- **Pink** — Discount pricing (discounted DBU rate and cost)
- **Green** — VM infrastructure costs (cloud provider)
- **Purple** — Total cost (DBU + VM combined)

Orange headers are used for general workload identity columns (name, type, configuration, SKU, notes) but are not listed in the legend section.

### 6. Assumptions & Notes

The bottom section documents:
- That all pricing uses Databricks list rates
- DBU rate source and lookup method
- How discount percentages are applied
- Export timestamp

## Formatting

The exported file includes professional formatting:
- **Color-coded column headers** matching the legend colors
- **Frozen panes** — the header row and first two columns stay visible when scrolling
- **Currency formatting** — all dollar amounts formatted as `$#,##0.00`
- **Percentage formatting** — discount column formatted as `0%`
- **Auto-sized columns** — widths adjust to content
- **Landscape orientation** — fits on standard paper for printing
- **Borders** — light grid lines for readability

## Common Use Cases

### RFP Response
Export your estimate to attach to a Request for Proposal. The professional formatting and complete cost breakdown make it ready for procurement teams. Adjust the discount percentage column to reflect your negotiated rates.

### Internal Planning
Use the export to share cost projections with stakeholders who don't have Lakemeter access. The formula-based cells let finance teams adjust assumptions (hours, discounts) directly in Excel.

### Vendor Comparison
Create separate estimates for different configurations (e.g., Classic vs Serverless, different instance types) and export both. Compare them side-by-side in Excel to find the most cost-effective option.

### Cost Modeling
Since all cells use formulas, you can build additional analysis on top of the export — add growth projections, what-if scenarios, or integrate it into a larger financial model.

## Tips

- Export **after** finalizing your estimate — the file reflects the exact state at download time
- The **discount percentage** column is editable in Excel. Set it to your negotiated rate and all costs recalculate
- For FMAPI workloads, the token configuration columns show your volume assumptions — adjust these for different usage scenarios
- Lakebase and Vector Search storage costs appear on separate rows. Make sure to include both rows when referencing total costs
