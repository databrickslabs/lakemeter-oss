# Pricing Sync Notebooks

**Author:** Steven Tan  
**Last Updated:** December 2025

Fetches and syncs Databricks pricing data to Unity Catalog tables.

---

## Notebook Execution Order

Run notebooks in this order:

| # | Notebook | Purpose | Output Table |
|---|----------|---------|--------------|
| 1 | `01_Fetch_DBU_Prices` | Fetch DBU prices from system tables | `dbu_prices`, `sku_region_mapping` |
| 2 | `02_Load_DBU_Rates` | Load instance DBU rates from Excel | `instance_rates` |
| 3 | `03_Fetch_AWS_VM` | Fetch AWS VM costs | `vm_costs` (AWS) |
| 4 | `04_Fetch_Azure_VM` | Fetch Azure VM costs | `vm_costs` (Azure) |
| 5 | `05_Fetch_GCP_VM` | Fetch GCP VM costs | `vm_costs` (GCP) |

### Optional / Debug Notebooks
| # | Notebook | Purpose |
|---|----------|---------|
| 98 | `98_Cost_Calculation_Examples` | End-to-end cost calculation examples |
| 99 | `99_Debug_Data_Quality` | Data quality checks and validation |

---

## Output Tables

All tables are created in: `lakemeter_catalog.lakemeter`

### Core Pricing Tables

| Table | Description | Primary Key |
|-------|-------------|-------------|
| `dbu_prices` | DBU prices by cloud/region/tier/product | `cloud, region, tier, product_type, sku_name` |
| `vm_costs` | VM costs by cloud/region/instance | `cloud, region, instance_type, pricing_tier, payment_option` |
| `instance_rates` | DBU rate per instance type | `cloud, instance_type` |
| `sku_region_mapping` | Maps SKU region names to region codes | `cloud, sku_region` |

### Product Rate Tables

| Table | Description |
|-------|-------------|
| `dbsql_rates` | DBSQL warehouse DBU/hour rates |
| `serverless_product_rates` | Vector Search, Model Serving rates |
| `fmapi_databricks_rates` | Databricks-hosted LLM rates |
| `fmapi_proprietary_rates` | External LLM rates (OpenAI, Anthropic, etc.) |

### Reference Tables

| Table | Description |
|-------|-------------|
| `dbu_multipliers` | Photon and other multipliers |
| `dbsql_warehouse_config` | DBSQL warehouse instance configurations |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                                 │
├─────────────────────────────────────────────────────────────────┤
│  System Tables          AWS/Azure/GCP APIs       Excel File     │
│  (billing.list_prices)  (VM pricing)             (DBU rates)    │
└──────────┬─────────────────────┬─────────────────────┬──────────┘
           │                     │                     │
           ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   UNITY CATALOG TABLES                           │
│  lakemeter_catalog.lakemeter.*                                  │
├─────────────────────────────────────────────────────────────────┤
│  dbu_prices │ vm_costs │ instance_rates │ product rates...      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │ Lakebase Sync (CDC)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LAKEBASE (Postgres)                         │
│  sync_pricing_dbu_rates │ sync_pricing_vm_costs │ sync_ref_*    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Set Up Catalog & Schema
```sql
CREATE CATALOG IF NOT EXISTS lakemeter_catalog;
CREATE SCHEMA IF NOT EXISTS lakemeter_catalog.lakemeter;
```

### 2. Run Notebooks
```python
# Run in Databricks
%run ./01_Fetch_DBU_Prices
%run ./02_Load_DBU_Rates
%run ./03_Fetch_AWS_VM
%run ./04_Fetch_Azure_VM
%run ./05_Fetch_GCP_VM
```

### 3. Verify Data
```sql
-- Check row counts
SELECT 'dbu_prices' as table_name, COUNT(*) as rows FROM lakemeter_catalog.lakemeter.dbu_prices
UNION ALL
SELECT 'vm_costs', COUNT(*) FROM lakemeter_catalog.lakemeter.vm_costs
UNION ALL
SELECT 'instance_rates', COUNT(*) FROM lakemeter_catalog.lakemeter.instance_rates;
```

---

## Sync to Lakebase

After running these notebooks, sync to Lakebase using:
- `../Lakebase_Setup/02_Create_Sync_Tables`

The sync creates tables with `sync_` prefix in Lakebase:
- `sync_pricing_dbu_rates`
- `sync_pricing_vm_costs`
- `sync_ref_instance_dbu_rates`
- etc.

---

## Refresh Schedule

| Data Source | Refresh Frequency | Notes |
|-------------|-------------------|-------|
| DBU Prices | Monthly | After Databricks price updates |
| VM Costs | Monthly | Cloud provider pricing changes |
| Instance Rates | Quarterly | When new instance types added |
| FMAPI Rates | As needed | When new models are released |

---

## Troubleshooting

### Missing Regions
```sql
-- Check which regions have DBU prices but no VM costs
SELECT DISTINCT cloud, region 
FROM lakemeter_catalog.lakemeter.dbu_prices 
WHERE region NOT IN (
    SELECT DISTINCT region FROM lakemeter_catalog.lakemeter.vm_costs
);
```

### Duplicate Keys
```sql
-- Check for duplicates in dbu_prices
SELECT cloud, region, tier, product_type, sku_name, COUNT(*) 
FROM lakemeter_catalog.lakemeter.dbu_prices 
GROUP BY 1,2,3,4,5 
HAVING COUNT(*) > 1;
```

### Run Debug Notebook
```python
%run ./99_Debug_Data_Quality
```

