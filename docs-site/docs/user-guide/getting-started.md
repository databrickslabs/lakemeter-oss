---
sidebar_position: 2
---

# 5-Minute Tutorial

This tutorial walks you through creating a real cost estimate from scratch. By the end, you will have a complete estimate for a data platform with two workloads on AWS, ready to export.

## Video walkthrough

<video controls width="100%" preload="metadata" aria-label="Getting Started tutorial video showing the end-to-end workflow: login, create estimate, add workloads, review costs, use AI assistant, and export to Excel">
  <source src="/lakemeter-oss/video/getting-started-tutorial.mp4" type="video/mp4" />
  Your browser does not support the video tag. <a href="/lakemeter-oss/video/getting-started-tutorial.mp4">Download the tutorial video</a>.
</video>

*End-to-end tutorial: create an estimate, add Lakeflow Jobs and Databricks SQL workloads, review costs, ask the AI assistant, and export to Excel.*

## What we are building

A cost estimate for a mid-size data platform running on **AWS us-east-1** with the **Premium** tier:

| Workload | Purpose | Configuration |
|----------|---------|---------------|
| ETL Pipeline | Nightly batch ingestion | Lakeflow Jobs, 4 workers, runs 2x/day for 45 min |
| Analytics Warehouse | Business intelligence queries | Databricks SQL Serverless, Small size, 10 hrs/day |

## Step 1: Create the estimate

1. Open Lakemeter in your browser. You are automatically signed in via Databricks SSO.
2. On the home page, click **New Estimate**.
3. Fill in the form:
   - **Estimate Name:** `Q4 Data Platform - AWS`
   - **Cloud:** `AWS`
   - **Region:** `us-east-1`
   - **Pricing Tier:** `Premium`
4. Click **Create**.

You land on the **Calculator** page -- an empty estimate ready for workloads.

![Creating an estimate in Lakemeter — click New Estimate, fill the form, and submit](/img/gifs/creating-estimate.gif)
*Animated: creating a new estimate — fill in name, cloud, region, and tier, then click Create.*

## Step 2: Add the ETL Pipeline workload (Lakeflow Jobs)

1. Click **Add Workload**.
2. Set **Workload Type** to **Lakeflow Jobs**.
3. Set **Workload Name** to `ETL Pipeline`.
4. Leave **Serverless** toggled off (we want classic compute for this example).
5. Configure compute (in the Driver Node and Worker Nodes cards):
   - **Driver Instance Type:** `m5d.xlarge`
   - **Worker Instance Type:** `m5d.xlarge`
   - **Worker Count:** `4`
   - **Photon:** Off (leave unchecked)
6. Configure pricing (within each card):
   - **Driver Pricing Tier:** On-Demand (the default)
   - **Worker Pricing Tier:** Spot Instances (the default)
7. Configure usage:
   - **Runs Per Day:** `2`
   - **Avg Runtime (minutes):** `45`
   - **Days Per Month:** `30` (the default is 22 business days — change it to 30 since this ETL runs every day including weekends)

8. Click **Save**.

**What the numbers mean:** This job runs twice daily for 45 minutes, so it uses 1.5 hours/day x 30 days = **45 compute-hours/month**. Lakemeter derives DBU consumption from the configured driver and workers, applies the rate for the estimate context, and adds the selected VM pricing assumptions.

## Step 3: Add the Analytics Warehouse workload (Databricks SQL)

1. Click **Add Workload** again.
2. Set **Workload Type** to **Databricks SQL**.
3. Set **Workload Name** to `Analytics Warehouse`.
4. Leave the **Serverless** checkbox checked (this is the default).
5. Set **Size** to **Small**.
6. Set **Number of Clusters** to `1`.
7. Configure usage:
   - **Hours Per Month:** `220` (roughly 10 hrs/day x 22 business days)

8. Click **Save**.

**What the numbers mean:** Lakemeter uses the selected warehouse size, monthly hours, cluster count, and the list rate resolved for the estimate context. Expand the saved workload to review the DBU quantity and rate used in the calculation.

## Step 4: Review costs

Back on the Calculator page, you can see:

- **Each workload's monthly cost** displayed on its card or row
- **Total estimate cost** summed at the top
- **DBU breakdown** showing how many Databricks Units each workload consumes

:::tip
Click on a workload to expand or edit it. Costs recalculate instantly when you change any parameter -- try adjusting the number of workers or warehouse size to see the impact.
:::

![Estimate with multiple workloads configured](/img/estimate-with-workloads.png)
*An estimate with multiple workloads showing individual costs and the total cost summary.*

## Step 5: Export to Excel

1. Click the **Export** button (download icon) at the top of the calculator page.
2. An Excel file downloads named something like `Databricks_Estimate_Q4_Data_Platform_AWS_20260404.xlsx`.

The spreadsheet includes:
- **Header section** with your estimate details (cloud, region, tier)
- **Workload table** with every configuration field, DBU rates, and costs per workload
- **Summary section** with total monthly cost and DBU breakdown by SKU type
- **Assumptions and notes** explaining the pricing basis

This file is ready to attach to an RFP response, share in a planning meeting, or use for internal budgeting.

## What to try next

- **Add more workloads** -- use the [Workload Sizing Guides](/user-guide/workloads) to choose another supported workload.
- **Use the AI Assistant** -- click the chat icon on the right side and describe what you need. For example: "Add a Lakeflow Spark Declarative Pipeline." The assistant proposes workload configurations you can accept or modify. See the [AI Assistant guide](/user-guide/ai-assistant).
- **Duplicate and compare** -- duplicate your estimate, change the region or tier, and compare costs side by side.
- **Follow the full workflow** -- see the [End-to-End Workflow](/user-guide/end-to-end-workflow) guide for a complete walkthrough from creation through export interpretation.
