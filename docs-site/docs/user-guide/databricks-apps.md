---
sidebar_position: 16
---

# Databricks Apps Sizing

> **Lakemeter UI name:** Databricks Apps

Use this guide to model monthly Databricks Apps consumption in Lakemeter. It explains the estimator inputs and calculation behavior, not Databricks Apps capabilities, configuration, or limits.

For current product guidance, start from the [official Databricks documentation](https://docs.databricks.com/). For current public rates, use the [Databricks pricing page](https://www.databricks.com/product/pricing) and the rate shown in Lakemeter.

## Form inputs

### App Size

Select the app size that represents the workload. The selected size determines the DBU-per-hour conversion used by Lakemeter.

Use the options shown in Lakemeter rather than copying an option inventory or conversion values from this guide. Confirm the appropriate size using current Databricks guidance and your own workload testing.

### Number of Apps

Enter the number of identically sized apps that use the same monthly schedule. Each app is billed independently, so this value multiplies the DBU consumption.

Create separate workload entries when apps use different sizes or operating schedules.

### Hours Per Month

Enter the expected billed uptime per app for one month.

For a schedule-based estimate:

```text
Hours per month
  = Active hours per day
  × Active days per month
```

## Expected monthly quantity

The monthly quantity is aggregate app-hours. Base it on the expected operating schedule rather than request count or user count.

```text
Aggregate app-hours = Number of apps × Hours per app
```

Include every period that should be represented as billed uptime. Group apps only when their size and schedule are the same.

## How Lakemeter calculates cost

Lakemeter resolves the DBU-per-hour conversion for the selected app size and the regional DBU price for the estimate context.

```text
Monthly DBUs
  = Number of apps
  × App hours per month
  × DBU per app-hour for the selected size

Monthly cost
  = Monthly DBUs
  × Regional price per DBU
```

The conversion and price values are intentionally not reproduced here because they can change. Review the values shown in Lakemeter and verify important estimates against current Databricks pricing.

This Lakemeter workload model does not add a separate VM infrastructure charge.

## What to review before saving

- Does the selected app size match the option intended for the workload?
- Does the app count include every identically configured app?
- Do monthly hours represent billed uptime rather than only periods of user activity?
- Are apps with different sizes or schedules modeled as separate workload entries?
- Does the estimate use the intended cloud, region, and pricing tier?
- Do the conversion and DBU price shown in Lakemeter match the current pricing source?

## Excel export

Each Databricks Apps workload is exported as one row. The configuration includes the selected size and app count. The row's DBU-per-hour value is the aggregate rate across all apps and is multiplied by monthly hours to calculate monthly DBUs.

Use the exported configuration and hours to trace the cost back to the workload assumptions. The VM cost fields remain zero because this Lakemeter workload model calculates the entry from DBU consumption only.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [SKU Explorer](./pricing/sku-explorer)
- [Official Databricks documentation](https://docs.databricks.com/)
- [Databricks pricing](https://www.databricks.com/product/pricing)
