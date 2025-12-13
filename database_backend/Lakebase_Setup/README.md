# Lakebase Setup - Database Schema & Testing

This folder contains the PostgreSQL schema definition and test notebooks for the Lakemeter application database (Lakebase).

---

## 📁 File Structure

### **Schema Definition (SQL)**

| File | Purpose | Run Order |
|------|---------|-----------|
| `00_Create_Lakebase_Role.sql` | Create dedicated sync role | 1️⃣ First |
| `01_Create_Tables.sql` | Application tables & reference data | 2️⃣ Second |
| `02_Create_Views.sql` | Cost calculation views | 4️⃣ Last |

### **Documentation**

| File | Purpose |
|------|---------|
| `DATABASE_DESIGN.md` | Complete schema documentation |
| `DEVELOPER_GUIDE.md` | API & frontend integration guide |
| `README.md` | This file |

### **Testing**

| File | Purpose |
|------|---------|
| `Test_01_JOBS_Classic.py` | Comprehensive test: JOBS Classic workload |
| `Debug_View_Joins.py` | Diagnostic: View join debugging |
| `Debug_VM_Pricing.py` | Diagnostic: VM pricing lookups |

### **Legacy/Deprecated**

| File | Status |
|------|--------|
| ~~`lakemeter_erd.sql`~~ | ❌ Removed - replaced by 01 + 02 |
| ~~`HOTFIX_Recreate_View.sql`~~ | ❌ Removed - use 02_Create_Views.sql |

---

## 🚀 Quick Start

### **Step 1: Create PostgreSQL Role**

```bash
psql -h instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com \
     -d lakemeter_pricing \
     -U admin \
     -f 00_Create_Lakebase_Role.sql
```

Creates `lakemeter_sync_role` with password `Lak3m3t3r_Sync_2024!`

---

### **Step 2: Create Application Tables**

```bash
psql -h instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com \
     -d lakemeter_pricing \
     -U lakemeter_sync_role \
     -f 01_Create_Tables.sql
```

**Creates:**
- `users` - Application users
- `estimates` - Customer cost estimates
- `line_items` - Individual workload configurations
- `ref_workload_types` - UI form configuration
- `templates` - Reusable estimate templates
- `conversation_messages` - LLM chat history
- `decision_records` - Design decisions log
- `sharing` - Estimate sharing links

---

### **Step 3: Sync Pricing Data**

Run Databricks notebooks in `../Pricing_Sync/` folder to populate:
- `sync_pricing_dbu_rates`
- `sync_pricing_vm_costs`
- `sync_product_dbsql_rates`
- `sync_product_serverless_rates`
- `sync_product_fmapi_databricks`
- `sync_product_fmapi_proprietary`
- `sync_ref_instance_dbu_rates`
- `sync_ref_dbu_multipliers`

---

### **Step 4: Create Cost Calculation Views**

```bash
psql -h instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com \
     -d lakemeter_pricing \
     -U lakemeter_sync_role \
     -f 02_Create_Views.sql
```

**Creates:**
- `v_line_items_with_costs` - Calculates DBU and VM costs
- `v_estimates_with_totals` - Aggregates per estimate

---

## 📊 Schema Changes (December 2025)

### **NEW: Separate Driver vs Worker Pricing**

**Problem:** Users couldn't specify different pricing tiers for driver and worker nodes.

**Solution:** Added separate columns to `line_items`:

| Column | Options | Description |
|--------|---------|-------------|
| `driver_pricing_tier` | on_demand, reserved_1y, reserved_3y | Driver pricing (NEVER spot) |
| `worker_pricing_tier` | on_demand, spot, reserved_1y, reserved_3y | Worker pricing (can be spot) |

**Example Use Cases:**
```sql
-- Scenario 1: Reserved driver + Spot workers (cost optimization)
driver_pricing_tier = 'reserved_1y'
worker_pricing_tier = 'spot'

-- Scenario 2: All on-demand (simplicity)
driver_pricing_tier = 'on_demand'
worker_pricing_tier = 'on_demand'

-- Scenario 3: Reserved driver + On-demand workers (flexibility)
driver_pricing_tier = 'reserved_3y'
worker_pricing_tier = 'on_demand'
```

**Legacy Columns (deprecated but kept for backward compatibility):**
- `vm_pricing_tier` - Falls back if driver/worker tiers not set
- `spot_percentage` - No longer used

---

## 🧪 Running Tests

### **Test 01: JOBS Classic Workload**

```python
# From Databricks workspace:
# /Workspace/Users/steven.tan@databricks.com/lakemeter/Lakebase_Setup/Test_01_JOBS_Classic.py

# Tests all payment option combinations:
# - AWS: 8 driver/worker pricing combos × 2 photon configs = 16 scenarios
# - Azure: 6 combos × 2 photon configs = 12 scenarios  
# - GCP: 6 combos × 2 photon configs = 12 scenarios
# TOTAL: 40 test scenarios
```

**Test Coverage:**
- ✅ All payment options (on_demand, spot, reserved_1y, reserved_3y)
- ✅ Driver vs worker pricing independence
- ✅ Photon enabled/disabled
- ✅ Multiple clouds (AWS, Azure, GCP)
- ✅ Automated validation with assertions

---

## 🔧 Troubleshooting

### **Views Show $0 Costs**

**Cause:** Missing pricing data in `sync_*` tables

**Debug:**
```python
# Run Debug_View_Joins.py to check:
# - Are line items attached to correct estimates?
# - Do instance types exist in sync_ref_instance_dbu_rates?
# - Do VM costs exist in sync_pricing_vm_costs?
# - Are multipliers present in sync_ref_dbu_multipliers?
```

### **View Creation Fails**

**Cause:** Missing `sync_*` tables

**Fix:** Run Pricing_Sync notebooks first to populate pricing data

### **Column Order Errors**

**Cause:** PostgreSQL doesn't allow column reordering with `CREATE OR REPLACE VIEW`

**Fix:** `02_Create_Views.sql` uses `DROP VIEW ... CREATE VIEW` to fully recreate

---

## 📚 Additional Resources

- **Full Schema Details:** [DATABASE_DESIGN.md](./DATABASE_DESIGN.md)
- **API Integration:** [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
- **Pricing Sync:** `../Pricing_Sync/README.md`
- **Salesforce Sync:** `../Salesforce_Sync/README.md`

---

## 🔄 Migration from Old Schema

If you have existing data using `vm_pricing_tier`:

```sql
-- Migrate to new columns (one-time)
UPDATE lakemeter.line_items
SET 
  driver_pricing_tier = CASE 
    WHEN vm_pricing_tier = 'spot' THEN 'on_demand'  -- Driver can't be spot
    ELSE vm_pricing_tier
  END,
  worker_pricing_tier = vm_pricing_tier
WHERE driver_pricing_tier IS NULL;
```

---

## 📞 Support

For questions or issues, contact the Lakemeter team or refer to the documentation above.

