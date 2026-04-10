---
sidebar_position: 17
---

# AI Parse (Document AI)

> **Lakemeter UI name:** AI Parse

AI Parse (Document AI) provides intelligent document parsing and extraction — converting PDFs, scanned images, and complex documents into structured data. Lakemeter supports two billing modes: **DBU-based** (direct DBU hours) and **Pages-based** (pages processed × complexity).

## When to use AI Parse

Use AI Parse when you need to **extract structured data from documents** — things like invoice processing, contract analysis, form digitization, or medical record parsing. If you need to call a language model for text generation or chat, see [FMAPI — Databricks Models](/user-guide/fmapi-databricks) instead.

## Real-world example

> **Scenario:** You are processing 50,000 scanned invoices per month on AWS us-east-1 (Premium tier). The invoices contain tables, logos, and multi-column layouts, so you classify them as "high" complexity. Each invoice is approximately 2 pages, totaling 100,000 pages per month.

### Configuration

| Field | Value |
|-------|-------|
| Workload Type | AI Parse |
| Billing Mode | Pages |
| Complexity | High |
| Pages (Thousands) | 100 |

### Step-by-step calculation

**1. DBU rate per 1,000 pages**

Each complexity level has a fixed DBU rate per 1,000 pages processed:

```
DBU per 1,000 Pages = 87.5 (High complexity)
```

**2. Monthly DBUs and cost**

```
Monthly DBUs = Pages (thousands) × DBU per 1,000 Pages
             = 100 × 87.5 = 8,750 DBUs
DBU Cost     = 8,750 × $0.07/DBU = $612.50
Total Cost   = $612.50 (no VM costs — always serverless)
```

:::note
These are example rates for illustration. Actual $/DBU depends on your cloud, region, and pricing tier. The $0.07 rate is the fallback for the `SERVERLESS_REAL_TIME_INFERENCE` SKU on AWS/us-east-1/Premium.
:::

### What about simpler documents?

For plain-text documents (letters, memos) with no tables or images:

```
DBU per 1,000 Pages = 12.5 (Low Text complexity)
Monthly DBUs        = 100 × 12.5 = 1,250 DBUs
Total Cost          = 1,250 × $0.07 = $87.50/month
```

That's **7× cheaper** than high complexity for the same page count.

## Billing modes

| Mode | How it works | Best for |
|------|-------------|----------|
| **Pages** | Pages (thousands) × complexity rate → DBUs | Document processing with known page counts |
| **DBU** | Direct DBU hours per month | Pre-calculated DBU budgets or mixed usage |

### Pages mode — complexity levels

| Complexity | DBU per 1,000 Pages | Document types |
|-----------|---------------------|----------------|
| **Low (Text)** | 12.5 | Plain text documents, letters, simple memos |
| **Low (Images)** | 22.5 | Documents with embedded images but simple layout |
| **Medium** | 62.5 | Mixed content — text with some tables and images |
| **High** | 87.5 | Complex layouts — multi-column, dense tables, forms, scanned images |

:::tip Choosing complexity
When in doubt, use **Medium**. Reserve **High** for documents with complex table extraction or multi-column scanned PDFs. Use **Low (Text)** only for well-structured digital PDFs with no images.
:::

## Configuration reference

| Field | Description | Default |
|-------|-------------|---------|
| **Billing Mode** | Pages or DBU. Pages mode uses complexity-based rates; DBU mode uses direct hours. | Pages |
| **Complexity** | Document complexity level (Pages mode only). Determines DBU rate per 1,000 pages. | Medium |
| **Pages (Thousands)** | Number of pages to process per month, in thousands (Pages mode only). | 100 |
| **Hours Per Month** | Direct DBU hours (DBU mode only). | 0 |

## How costs are calculated

### Pages mode

```
DBU/1000 Pages = Complexity Rate Lookup[complexity]
Monthly DBUs   = Pages (thousands) × DBU/1000 Pages
DBU Cost       = Monthly DBUs × $/DBU
Total Cost     = DBU Cost (no VM costs — always serverless)
```

### DBU mode

```
Monthly DBUs = Hours Per Month (direct input)
DBU Cost     = Monthly DBUs × $/DBU
Total Cost   = DBU Cost
```

### SKU mapping

| Workload | SKU | Fallback $/DBU |
|----------|-----|----------------|
| AI Parse (all modes) | `SERVERLESS_REAL_TIME_INFERENCE` | $0.07 |

## Tips

- **Estimate page counts accurately**: If you process 10,000 invoices with an average of 3 pages each, that's 30,000 pages = 30 thousands. Don't confuse document count with page count.
- **Batch by complexity**: If you have a mix of simple and complex documents, create separate workload entries for each complexity level to get a more accurate estimate.
- **Pages mode is usually clearer**: Unless you already know your DBU budget, Pages mode gives a more intuitive estimate based on actual document volumes.

## Common mistakes

- **Confusing thousands with actual page count**: The Pages field is in **thousands**. If you process 50,000 pages/month, enter 50, not 50,000.
- **Over-classifying complexity**: Not every document is "High" complexity. A well-formatted digital PDF with a simple table is "Medium" at most. Over-classifying inflates your estimate by up to 7×.
- **Expecting VM costs**: AI Parse is always serverless. $0 VM cost is correct.

## Excel export

Each AI Parse workload appears as one row in the exported spreadsheet:

| Column | What it shows |
|--------|--------------|
| Configuration | Billing mode + complexity (if Pages mode) |
| Mode | Serverless (always) |
| SKU | `SERVERLESS_REAL_TIME_INFERENCE` |
| Monthly DBUs | Calculated from pages × complexity rate |
| DBU Cost (List) | At list price |
| DBU Cost (Discounted) | At negotiated rate |
| VM Cost | $0 (always serverless) |
| Total Cost | DBU Cost |
