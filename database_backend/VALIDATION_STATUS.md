# 🔍 Validation Status for All Calculation Endpoints

## Summary of Applied Validations

### ✅ **1. JOBS Classic** `/api/v1/calculate/jobs-classic`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ Driver instance type validation (`validate_instance_type`)
- ✅ Worker instance type validation (`validate_instance_type`)
- ✅ Driver pricing tier validation with spot check (`validate_pricing_tier`, `is_driver=True`)
- ✅ Worker pricing tier validation (`validate_pricing_tier`, `is_driver=False`)
- ✅ Driver payment option validation (`validate_payment_option`)
- ✅ Worker payment option validation (`validate_payment_option`)
- ✅ Usage parameter validation (either run-based OR hours_per_month)

**Status:** ✅ COMPLETE

---

### ✅ **2. All-Purpose Classic** `/api/v1/calculate/all-purpose-classic`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ Driver instance type validation (`validate_instance_type`)
- ✅ Worker instance type validation (`validate_instance_type`)
- ✅ Driver pricing tier validation with spot check (`validate_pricing_tier`, `is_driver=True`)
- ✅ Worker pricing tier validation (`validate_pricing_tier`, `is_driver=False`)
- ✅ Driver payment option validation (`validate_payment_option`)
- ✅ Worker payment option validation (`validate_payment_option`)
- ✅ Usage parameter validation (either run-based OR hours_per_month)

**Status:** ✅ COMPLETE

---

### ⚠️ **3. JOBS Serverless** `/api/v1/calculate/jobs-serverless`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ Driver instance type validation (`validate_instance_type`)
- ✅ Worker instance type validation (`validate_instance_type`)
- ✅ Serverless mode validation (hardcoded: standard, performance)
- ✅ Usage parameter validation (either run-based OR hours_per_month)
- ❌ **MISSING**: Pricing tier validation (not needed for serverless)
- ❌ **MISSING**: Payment option validation (not needed for serverless)

**Status:** ✅ COMPLETE (no pricing/payment options for serverless)

---

### ✅ **4. DBSQL** `/api/v1/calculate/dbsql`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ Warehouse type validation (`validate_warehouse_type`)
- ✅ Warehouse size validation (`validate_warehouse_size`)
- ✅ VM pricing tier validation (for non-serverless only) (`validate_pricing_tier`)
- ✅ VM payment option validation (for non-serverless only) (`validate_payment_option`)

**Status:** ✅ COMPLETE

---

### ✅ **5. DLT** `/api/v1/calculate/dlt`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ DLT edition validation (hardcoded: CORE, PRO, ADVANCED)
- ✅ Driver instance type validation (`validate_instance_type`)
- ✅ Worker instance type validation (`validate_instance_type`)
- ✅ Driver pricing tier validation with spot check (`validate_pricing_tier`, `is_driver=True`)
- ✅ Worker pricing tier validation (`validate_pricing_tier`, `is_driver=False`)
- ✅ Driver payment option validation (`validate_payment_option`)
- ✅ Worker payment option validation (`validate_payment_option`)

**Status:** ✅ COMPLETE

---

### ✅ **6. Vector Search** `/api/v1/calculate/vector-search`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ Vector Search mode validation (`validate_vector_search_mode`)

**Status:** ✅ COMPLETE (serverless, no instance types)

---

### ⚠️ **7. Model Serving** `/api/v1/calculate/model-serving`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ GPU type validation (inline query check)

**Status:** ✅ COMPLETE (serverless, inline GPU validation)

---

### ⚠️ **8. FMAPI** `/api/v1/calculate/fmapi`

**Applied Validations:**
- ✅ Cloud validation (`validate_cloud`)
- ✅ Region validation (`validate_region`)
- ✅ Tier validation (`validate_tier`)
- ✅ Provider validation (conditional)
- ✅ Model validation (conditional: databricks or proprietary)
- ✅ Rate type validation (conditional: databricks or proprietary)

**Status:** ✅ COMPLETE (serverless, dynamic validation)

---

### ✅ **9. Lakebase** `/api/v1/calculate/lakebase`

**Applied Validations:**
- ✅ CU size validation (`validate_lakebase_cu_size`)
- ✅ Number of nodes validation (`validate_lakebase_num_nodes`)

**Status:** ✅ COMPLETE (cloud-agnostic, no cloud/region validation needed)

---

## 📊 Validation Coverage Summary

| Endpoint | Cloud | Region | Tier | Instance Type | Pricing | Payment | Special |
|----------|-------|--------|------|---------------|---------|---------|---------|
| JOBS Classic | ✅ | ✅ | ✅ | ✅ (D+W) | ✅ | ✅ | Usage params |
| All-Purpose Classic | ✅ | ✅ | ✅ | ✅ (D+W) | ✅ | ✅ | Usage params |
| JOBS Serverless | ✅ | ✅ | ✅ | ✅ (D+W) | N/A | N/A | Mode, Usage params |
| DBSQL | ✅ | ✅ | ✅ | N/A | ✅ | ✅ | Warehouse type/size |
| DLT | ✅ | ✅ | ✅ | ✅ (D+W) | ✅ | ✅ | DLT edition |
| Vector Search | ✅ | ✅ | ✅ | N/A | N/A | N/A | Mode |
| Model Serving | ✅ | ✅ | ✅ | N/A | N/A | N/A | GPU type |
| FMAPI | ✅ | ✅ | ✅ | N/A | N/A | N/A | Provider, Model |
| Lakebase | N/A | N/A | N/A | N/A | N/A | N/A | CU size, Nodes |

**Legend:**
- ✅ = Validation applied
- N/A = Not applicable for this workload type
- (D+W) = Driver and Worker

---

## 🎯 Key Validation Rules

### **Driver Pricing Tier**
- ❌ **Cannot be `spot`** (driver must be stable)
- ✅ Can be: `on_demand`, `reserved_1y`, `reserved_3y`

### **Worker Pricing Tier**
- ✅ Can be: `on_demand`, `spot`, `reserved_1y`, `reserved_3y`

### **Payment Options**
- Valid values: `NA`, `no_upfront`, `partial_upfront`, `all_upfront`
- Only applicable for reserved instances (`reserved_1y`, `reserved_3y`)

### **Instance Types**
- Must be cloud-specific (e.g., `m5.xlarge` for AWS, not for AZURE)
- Validated against `sync_ref_instance_dbu_rates` table

### **Usage Parameters (JOBS Classic, All-Purpose Classic, JOBS Serverless)**
- Must provide **EITHER**:
  - Run-based: `runs_per_day` + `avg_runtime_minutes` (+ optional `days_per_month`)
  - OR Direct: `hours_per_month`
- Cannot provide both methods

---

## ✅ All Endpoints Validated

**All calculation endpoints now have comprehensive validation applied!**

- Error messages include `code`, `message`, `field`, and `allowed_values`
- Consistent error response format across all endpoints
- Cloud-specific validations (e.g., Azure cannot have ENTERPRISE tier)
- Instance type validations prevent cross-cloud errors
- Driver spot protection prevents unstable clusters

---

**Last Updated:** December 18, 2025

