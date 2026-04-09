---
sidebar_position: 3
---

# Creating Estimates

An estimate is the top-level container for your Databricks cost analysis. Each estimate holds one or more workloads and is scoped to a specific cloud, region, and pricing tier.

![Lakemeter estimates list](/img/estimates-list.png)
*The estimates list page — create, search, and manage your cost estimates.*

![Creating an estimate — click New Estimate, fill the form, and submit](/img/gifs/creating-estimate.gif)
*Animated: the full estimate creation flow — enter a name, select cloud, region, and pricing tier, then click Create.*

## Estimate Fields

| Field | Required | Description |
|-------|----------|-------------|
| **Estimate Name** | Yes | A descriptive name for your estimate |
| **Cloud** | Yes | Cloud provider: `aws`, `azure`, or `gcp` |
| **Region** | Yes | Deployment region (options depend on selected cloud) |
| **Tier** | Yes | Pricing tier: Standard, Premium, or Enterprise |

## Creating a New Estimate

1. Navigate to the **Estimates** page
2. Click **New Estimate**
3. Fill in the required fields
4. Click **Create**

You'll be redirected to the calculator page where you can start adding workloads.

![Calculator page with workloads and cost summary](/img/calculator-overview.png)
*After creating an estimate, the calculator page is where you add and configure workloads.*

## Managing Estimates

### Viewing Estimates

The estimates list page shows all your estimates with:
- Estimate name
- Number of workloads (line items)
- Creation and last updated dates
- Current status

Use the search bar to filter estimates by name.

### Editing an Estimate

Click on any estimate to open it in the calculator. You can:
- Update the estimate name, region, or tier
- Add, edit, or remove workloads
- Reorder workloads by dragging

![Drag and drop to reorder workloads in the estimate](/img/gifs/drag-and-drop.gif)
*Animated: drag workloads to reorder them — the display order updates instantly.*

:::caution
Changing the **cloud provider** is blocked if the estimate already has workloads, since pricing and available instance types differ between clouds.
:::

### Duplicating an Estimate

To create a copy of an existing estimate:

1. Open the estimate
2. Click **Duplicate**

The copy includes all workloads and their configurations. The new estimate is named with a "(Copy)" suffix.

### Deleting an Estimate

Estimates are soft-deleted — they're hidden from the list but preserved in the database. Only the estimate owner can delete it.

## Estimate Statuses

| Status | Description |
|--------|-------------|
| **Draft** | Work in progress (default) |
| **Approved** | Finalized and approved |

## Versioning

Each save to an estimate increments its version number. This helps track changes over time.
