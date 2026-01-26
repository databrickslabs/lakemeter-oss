# Salesforce Sync to Lakebase

Syncs Salesforce data from Unity Catalog to Lakebase via Azure Storage.

## Data Flow

```
Logfood Workspace          Azure Storage           Lakemeter Workspace
┌─────────────────┐       ┌─────────────┐        ┌─────────────────┐
│ Unity Catalog   │  ──►  │  lakemeter  │  ──►   │    Lakebase     │
│ (Salesforce)    │       │  container  │        │   (PostgreSQL)  │
└─────────────────┘       └─────────────┘        └─────────────────┘
   01_Sync_To_Storage        Delta files        02_Import_From_Storage
```

## Tables

| Source Table | Storage Path | Target Table |
|--------------|--------------|--------------|
| `main.metric_store.dim_salesforce_account` | `/salesforce_sync/dim_salesforce_account` | `lakemeter.sync_dim_salesforce_account` |
| `main.metric_store.fct_salesforce_use_case__core` | `/salesforce_sync/fct_salesforce_use_case` | `lakemeter.sync_fct_salesforce_use_case` |
| `main.sfdc_bronze.hourly_opportunity` | `/salesforce_sync/hourly_opportunity` | `lakemeter.sync_hourly_opportunity` |

## Run Order

| Step | Notebook | Workspace | Action |
|------|----------|-----------|--------|
| 1 | `01_Sync_To_Storage` | **Logfood** | Export to Azure Storage |
| 2 | `02_Import_From_Storage` | **Lakemeter** | Import to Lakebase |

## Azure Storage

| Parameter | Value |
|-----------|-------|
| **Account** | `lakemeter` |
| **Container** | `lakemeter` |
| **Path** | `/salesforce_sync/` |

## Notebooks

| Notebook | Workspace | Description |
|----------|-----------|-------------|
| `01_Sync_To_Storage` | Logfood | Export tables to Azure Storage |
| `02_Import_From_Storage` | Lakemeter | Import from storage to Lakebase |

---
*Author: Steven Tan*

