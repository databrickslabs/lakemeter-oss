# Lakebase Setup - Organized Structure

This folder contains all scripts for setting up and testing the Lakemeter Lakebase (PostgreSQL) database.

## 📁 Folder Structure

```
Lakebase_Setup/
├── 1_Setup/              Setup & schema scripts (RUN THESE FIRST!)
├── 2_Tests/              Test notebooks for all workload types
├── 3_Debug/              Diagnostic & debug tools
├── 4_Documentation/      Documentation files
└── 5_Archive/            Old/reference SQL files
```

---

## 📂 1_Setup/ - Core Setup Scripts

**Run these in order to set up your database:**

| File | Purpose | When to Run |
|------|---------|-------------|
| `00_Create_Lakebase_Role.sql` | Creates PostgreSQL role with permissions | **FIRST** - Before any other script |
| `01_Create_Tables.py` | Creates all application tables & reference data | **SECOND** - After role creation |
| `02_Create_Views.py` | Creates cost calculation views | **THIRD** - After tables are created |
| `FIX_Test04_Product_Type.sql` | Quick fix for product_type mismatch | **OPTIONAL** - If Test_04 shows $0 costs |

### Quick Start:
```bash
# 1. Run in Lakebase SQL Editor
00_Create_Lakebase_Role.sql

# 2. Run in Databricks
01_Create_Tables.py
02_Create_Views.py

# 3. Verify
Any Test_*.py notebook
```

---

## 📂 2_Tests/ - Test Notebooks (14 notebooks)

Comprehensive test cases for all workload types covering:
- All 3 clouds (AWS, AZURE, GCP)
- Multiple regions (US + Europe)
- All 3 tiers (STANDARD, PREMIUM, ENTERPRISE)

| # | Notebook | Workload Type | Coverage |
|---|----------|---------------|----------|
| 01 | `Test_01_JOBS_Classic.py` | JOBS Classic | All payment options (on-demand, spot, reserved 1y/3y) |
| 02 | `Test_02_JOBS_Serverless.py` | JOBS Serverless | Standard + Performance modes |
| 03 | `Test_03_ALL_PURPOSE_Classic.py` | ALL_PURPOSE Classic | On-demand, spot, reserved 1y |
| 04 | `Test_04_ALL_PURPOSE_Serverless.py` | ALL_PURPOSE Serverless | Standard mode only |
| 05 | `Test_05_DLT_Classic.py` | DLT Classic | All editions (Core, Pro, Advanced) |
| 06 | `Test_06_DLT_Serverless.py` | DLT Serverless | Standard + Performance, Continuous + Triggered |
| 07 | `Test_07_DBSQL_Classic.py` | DBSQL Classic | T-shirt sizes (2X-Small to 4X-Large) |
| 08 | `Test_08_DBSQL_Pro.py` | DBSQL Pro | T-shirt sizes |
| 09 | `Test_09_DBSQL_Serverless.py` | DBSQL Serverless | Serverless warehouse |
| 10 | `Test_10_Vector_Search.py` | Vector Search | Standard + Storage-optimized |
| 11 | `Test_11_Model_Serving.py` | Model Serving | CPU, GPU (small/medium/large) |
| 12 | `Test_12_FMAPI_Databricks.py` | FMAPI (Databricks) | Llama, DBRX models |
| 13 | `Test_13_FMAPI_Proprietary.py` | FMAPI (Proprietary) | OpenAI, Anthropic, Google |
| 14 | `Test_14_LAKEBASE.py` | LAKEBASE | 1/2/4/8 CU configurations |

### How to Run Tests:
1. Ensure `1_Setup/` scripts have been run first
2. Open any test notebook in Databricks
3. Run all cells
4. Check output for validation results

### Expected Output:
- ✅ Green checkmarks = Tests passed
- ❌ Red X = Tests failed (investigate with debug tools)
- Detailed cost breakdown for each scenario
- Manual validation with assertions

---

## 📂 3_Debug/ - Diagnostic & Debug Tools

Use these when tests show unexpected results (e.g., $0 costs).

| File | Purpose | When to Use |
|------|---------|-------------|
| `Debug_Test_04_Serverless.py` | Diagnose Test_04 ALL_PURPOSE Serverless $0 costs | If Test_04 shows $0 |
| `Debug_Test_06_DLT_Serverless.py` | Diagnose Test_06 DLT Serverless $0 costs | If Test_06 shows $0 |
| `Debug_VM_Pricing.py` | Diagnose VM pricing issues (Azure/GCP $0) | If classic tests show $0 VM costs |
| `Quick_Diagnostic_Test04.sql` | Fast SQL diagnostic for Test_04 | Quick check in SQL Editor |

### How to Debug:
1. Note which test is failing (e.g., Test_06 shows $0 costs)
2. Run corresponding debug notebook (e.g., `Debug_Test_06_DLT_Serverless.py`)
3. Review output for ❌ errors
4. Apply fixes based on findings

### Common Issues:
- **Product type mismatch:** View uses wrong `product_type` string
- **Missing pricing data:** `sync_pricing_dbu_rates` table incomplete
- **Region name mismatch:** Test uses different region names than pricing
- **Missing instance DBU rates:** `sync_ref_instance_dbu_rates` incomplete

---

## 📂 4_Documentation/ - Documentation Files

| File | Contents |
|------|----------|
| `DATABASE_DESIGN.md` | Complete database schema documentation |
| `DEVELOPER_GUIDE.md` | Developer guide for working with Lakebase |
| `EXECUTION_GUIDE.md` | Step-by-step execution guide |
| `OWNERSHIP_TROUBLESHOOTING.md` | Troubleshooting ownership issues |

---

## 📂 5_Archive/ - Old/Reference Files

Contains old SQL versions and troubleshooting scripts for reference.
**You typically don't need to run these files** - they're kept for historical reference.

---

## 🚀 Quick Start Guide

### First Time Setup:
```bash
# 1. Create database role
Run: 1_Setup/00_Create_Lakebase_Role.sql in Lakebase SQL Editor

# 2. Create tables
Run: 1_Setup/01_Create_Tables.py in Databricks

# 3. Create views
Run: 1_Setup/02_Create_Views.py in Databricks

# 4. Run a test to verify
Run: 2_Tests/Test_01_JOBS_Classic.py in Databricks
```

### If Tests Show $0 Costs:
```bash
# 1. Run debug notebook
Run: 3_Debug/Debug_Test_0X_<workload>.py

# 2. Look for ❌ errors in output

# 3. Common fixes:
#    - Product type mismatch: Run 02_Create_Views.py
#    - Missing pricing: Re-run Pricing_Sync notebooks
#    - Wrong regions: Update test to use correct region names
```

---

## 🔍 Troubleshooting

### Problem: All costs show $0

**Solution:** Run the corresponding debug notebook:
- Test_04 → `Debug_Test_04_Serverless.py`
- Test_06 → `Debug_Test_06_DLT_Serverless.py`
- VM costs → `Debug_VM_Pricing.py`

### Problem: CheckViolation or UndefinedColumn errors

**Solution:** All tests have been fixed for these common errors:
- ✅ `vm_payment_option` uses lowercase values
- ✅ `description` column removed
- ✅ `dbu_price` → `price_per_dbu` (correct column name)
- ✅ Complete tuples in INSERT statements

### Problem: "must be owner of table" errors

**Solution:** See `4_Documentation/OWNERSHIP_TROUBLESHOOTING.md`

---

## 📊 Test Coverage Summary

| Cloud | Regions Tested | Tiers Tested | Workload Types | Total Scenarios |
|-------|----------------|--------------|----------------|-----------------|
| AWS | us-east-1, eu-west-1 | STANDARD, PREMIUM, ENTERPRISE | All 8 types | ~200 |
| AZURE | eastus, westeurope | STANDARD, PREMIUM | All 8 types | ~150 |
| GCP | us-central1, europe-west1 | STANDARD, PREMIUM, ENTERPRISE | All 8 types | ~200 |

**Total:** 550+ test scenarios across all notebooks!

---

## 🎯 Success Criteria

After running all tests, you should see:
- ✅ Positive costs for PREMIUM/ENTERPRISE tiers
- ✅ $0 costs for STANDARD tier serverless (valid - not available)
- ✅ All validation checks passed
- ✅ Detailed cost breakdowns with DBU and VM costs
- ✅ No errors or warnings

---

## 📞 Need Help?

1. Check `4_Documentation/` for detailed guides
2. Run debug notebooks in `3_Debug/` to diagnose issues
3. Review test output for specific error messages
4. Check `5_Archive/OWNERSHIP_TROUBLESHOOTING.md` for permission issues

---

**Last Updated:** December 2025  
**Version:** 2.0 (Organized Structure)

