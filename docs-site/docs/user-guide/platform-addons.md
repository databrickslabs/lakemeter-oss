---
sidebar_position: 22
---

# Platform Add-ons

Platform Add-ons are estimate-level charges calculated as a percentage of eligible Databricks product spend. They are not independent workloads.

Select an add-on beside the estimate cloud and pricing tier. Lakemeter validates whether the add-on is available for that combination.

## Product Spend at List

Lakemeter calculates the add-on from Databricks product spend before negotiated discounts:

```text
Product Spend at List
  = DBU list cost
  + DSU list cost
```

Cloud VM infrastructure cost is excluded. The add-on is also excluded from its own calculation base, preventing compounding.

## Available add-ons

### Enhanced Security and Compliance

- AWS Enterprise: 15%
- Azure Premium: 10%
- GCP Enterprise: 15%

### Mission Critical

Mission Critical includes Enhanced Security and Compliance, so the two cannot be selected together.

- AWS Enterprise: standard 30%
- Azure Premium: standard 30%
- Promotional rate: 15% through June 30, 2027

Mission Critical is not present in the current GCP pricing catalog.

Rates and eligibility reflect the pricing catalog bundled with the release. Confirm current eligibility and commercial terms before sharing a final estimate.

## How Lakemeter calculates cost

```text
Add-on list cost
  = Product Spend at List × Active uplift percentage

Add-on cost after discount
  = Add-on list cost × (1 − Add-on discount percentage)

Grand total
  = Workload cost after discounts
  + Add-on cost after discount
```

Workload discounts do not reduce the add-on calculation base. A separate Platform Add-on discount can be applied after the uplift.

## What to review

- Is the estimate cloud and tier eligible?
- Is the selected add-on the intended package?
- Is a time-limited promotional rate active for the pricing date?
- Does Product Spend at List contain DBU and DSU list cost but exclude VM cost?
- Is the negotiated add-on discount separate from workload discounts?
- Does the grand total include both workloads and the add-on?

## Excel export

The workbook separates the estimate into:

1. Workload detail rows
2. Workload cost summary before Platform Add-ons
3. Platform Add-on summary
4. Final estimate summary

The add-on section shows Product Spend at List, the active uplift, promotion details when applicable, list add-on cost, negotiated discount, and discounted add-on cost. The final section combines workloads and add-ons into monthly and annual totals.

## Related

- [Calculation Reference](./calculation-reference)
- [Exporting to Excel](./exporting)
- [Databricks pricing](https://www.databricks.com/product/pricing/platform-addons)
