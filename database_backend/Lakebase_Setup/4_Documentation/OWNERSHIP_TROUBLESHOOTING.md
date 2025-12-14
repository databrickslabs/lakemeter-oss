# PostgreSQL Ownership & Permissions Troubleshooting

## 🐛 The Problem

```
❌ Drop v_estimates_with_totals
   Error: must be owner of view v_estimates_with_totals
```

### Why This Happens

In PostgreSQL:
- `ALL PRIVILEGES` ≠ **Ownership**
- Only the **owner** (or superuser) can `DROP` objects
- Your `lakemeter_sync_role` can read/write data, but **can't drop** tables/views it doesn't own

### Who Owns Your Objects?

Objects are owned by whoever created them:
- If you created tables using the **Lakebase SQL Editor** (logged in as `admin`), owner = `admin`
- If you created tables using **`lakemeter_sync_role`** (from notebooks), owner = `lakemeter_sync_role`

---

## ✅ Solution 1: Transfer Ownership (Recommended)

**Best for:** Existing objects you want to keep

### Step 1: Run as Admin User

Open **Lakebase SQL Editor** and run:

```sql
-- Check current ownership
SELECT 
    schemaname, tablename, tableowner
FROM pg_tables
WHERE schemaname = 'lakemeter'
ORDER BY tablename;
```

### Step 2: Transfer Ownership

Run the script: `00_Transfer_Ownership.sql`

```sql
-- Transfer views (must be done first)
ALTER VIEW lakemeter.v_estimates_with_totals OWNER TO lakemeter_sync_role;
ALTER VIEW lakemeter.v_line_items_with_costs OWNER TO lakemeter_sync_role;

-- Transfer tables
ALTER TABLE lakemeter.users OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.templates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.estimates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.line_items OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.ref_workload_types OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.ref_cloud_tiers OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.conversation_messages OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.decision_records OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sharing OWNER TO lakemeter_sync_role;

-- Transfer all sync_* tables
ALTER TABLE lakemeter.sync_ref_sku_region_map OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_ref_instance_dbu_rates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_ref_dbu_multipliers OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_pricing_dbu_rates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_pricing_vm_costs OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_product_dbsql_rates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_product_serverless_rates OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_product_fmapi_databricks OWNER TO lakemeter_sync_role;
ALTER TABLE lakemeter.sync_product_fmapi_proprietary OWNER TO lakemeter_sync_role;
```

### Step 3: Verify

```sql
SELECT 
    'Table' as object_type,
    tablename as object_name,
    tableowner as owner,
    CASE WHEN tableowner = 'lakemeter_sync_role' THEN '✅' ELSE '❌' END as status
FROM pg_tables
WHERE schemaname = 'lakemeter'
UNION ALL
SELECT 
    'View' as object_type,
    viewname as object_name,
    viewowner as owner,
    CASE WHEN viewowner = 'lakemeter_sync_role' THEN '✅' ELSE '❌' END as status
FROM pg_views
WHERE schemaname = 'lakemeter'
ORDER BY object_type, object_name;
```

**Expected:** All objects show ✅

### Step 4: Re-run Your Notebook

Now `01_Create_Tables.py` will work! The role can now drop objects it owns.

---

## ✅ Solution 2: Grant Superuser (Use with Caution)

**Best for:** Development/testing environments

### ⚠️ Warning

Superuser has **unlimited privileges**:
- Can drop any database
- Can modify any table
- Can create/delete users
- Bypasses all permission checks

**NOT recommended for production!**

### How to Grant Superuser

Run as admin user in Lakebase SQL Editor:

```sql
-- Grant superuser
ALTER ROLE lakemeter_sync_role WITH SUPERUSER;

-- Verify
SELECT 
    rolname,
    rolsuper as is_superuser,
    CASE WHEN rolsuper THEN '✅ SUPERUSER' ELSE '❌ NOT SUPERUSER' END as status
FROM pg_roles
WHERE rolname = 'lakemeter_sync_role';
```

**Expected output:**
```
rolname              | is_superuser | status
---------------------+--------------+----------------
lakemeter_sync_role  | t            | ✅ SUPERUSER
```

### To Revoke Later

```sql
ALTER ROLE lakemeter_sync_role WITH NOSUPERUSER;
```

---

## ✅ Solution 3: Drop Using Admin, Recreate Using Role

**Best for:** Fresh start with correct ownership from the beginning

### Step 1: Drop All Objects as Admin

Run in Lakebase SQL Editor (as admin):

```sql
-- Drop views first (depend on tables)
DROP VIEW IF EXISTS lakemeter.v_estimates_with_totals CASCADE;
DROP VIEW IF EXISTS lakemeter.v_line_items_with_costs CASCADE;

-- Drop tables
DROP TABLE IF EXISTS lakemeter.decision_records CASCADE;
DROP TABLE IF EXISTS lakemeter.conversation_messages CASCADE;
DROP TABLE IF EXISTS lakemeter.sharing CASCADE;
DROP TABLE IF EXISTS lakemeter.line_items CASCADE;
DROP TABLE IF EXISTS lakemeter.estimates CASCADE;
DROP TABLE IF EXISTS lakemeter.templates CASCADE;
DROP TABLE IF EXISTS lakemeter.users CASCADE;
DROP TABLE IF EXISTS lakemeter.ref_cloud_tiers CASCADE;
DROP TABLE IF EXISTS lakemeter.ref_workload_types CASCADE;
```

### Step 2: Run Notebooks

Now run `01_Create_Tables.py` - it will create objects owned by `lakemeter_sync_role` from the start!

---

## 📊 Comparison

| Solution | Pros | Cons | Best For |
|----------|------|------|----------|
| **1. Transfer Ownership** | ✅ Safe<br>✅ Keeps data<br>✅ Granular control | ⚠️ Requires admin access | Existing production data |
| **2. Grant Superuser** | ✅ Simple<br>✅ One command | ❌ Security risk<br>❌ Too much power | Dev/test only |
| **3. Drop & Recreate** | ✅ Clean slate<br>✅ Correct from start | ❌ Loses data<br>❌ Downtime | Fresh setup |

---

## 🎯 Recommended Approach

### For Development (Now)
1. **Grant Superuser** (Solution 2) for quick testing
2. Later, revoke superuser and transfer ownership

### For Production (Later)
1. **Transfer Ownership** (Solution 1) for all objects
2. Ensure all future objects are created by `lakemeter_sync_role`
3. Never use superuser in production

---

## 🔍 Understanding PostgreSQL Permissions

### Ownership vs Privileges

```
Owner:
  • Can DROP, ALTER, GRANT on object
  • Has all privileges by default
  • Only ONE owner per object

Privileges (GRANT):
  • SELECT, INSERT, UPDATE, DELETE
  • Can be granted to multiple roles
  • Does NOT include DROP/ALTER
```

### What `ALL PRIVILEGES` Includes

```sql
GRANT ALL PRIVILEGES ON TABLE foo TO lakemeter_sync_role;
```

**Includes:**
- ✅ SELECT (read data)
- ✅ INSERT (add rows)
- ✅ UPDATE (modify rows)
- ✅ DELETE (remove rows)
- ✅ TRUNCATE (remove all rows fast)
- ✅ REFERENCES (create foreign keys)
- ✅ TRIGGER (create triggers)

**Does NOT include:**
- ❌ DROP (delete table)
- ❌ ALTER (modify structure)
- ❌ GRANT (give permissions to others)

### To Get Full Control

You need **both**:
1. **Ownership** (via `ALTER TABLE ... OWNER TO`) OR **Superuser**
2. **Privileges** (via `GRANT ALL`)

---

## 🛠️ Quick Commands

### Check Who Owns What

```sql
-- Tables
SELECT schemaname, tablename, tableowner 
FROM pg_tables 
WHERE schemaname = 'lakemeter';

-- Views
SELECT schemaname, viewname, viewowner 
FROM pg_views 
WHERE schemaname = 'lakemeter';
```

### Check Role Privileges

```sql
-- Check if superuser
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole
FROM pg_roles
WHERE rolname = 'lakemeter_sync_role';

-- Check table privileges
SELECT grantee, privilege_type, table_name
FROM information_schema.table_privileges
WHERE grantee = 'lakemeter_sync_role'
AND table_schema = 'lakemeter';
```

### Bulk Transfer Ownership (Dynamic SQL)

```sql
-- Generate ALTER statements for all tables
SELECT 'ALTER TABLE lakemeter.' || tablename || ' OWNER TO lakemeter_sync_role;'
FROM pg_tables
WHERE schemaname = 'lakemeter'
AND tableowner != 'lakemeter_sync_role';

-- Generate ALTER statements for all views
SELECT 'ALTER VIEW lakemeter.' || viewname || ' OWNER TO lakemeter_sync_role;'
FROM pg_views
WHERE schemaname = 'lakemeter'
AND viewowner != 'lakemeter_sync_role';
```

---

## 📝 Files to Use

| File | Purpose | Run As |
|------|---------|--------|
| `00_Transfer_Ownership.sql` | Transfer ownership to lakemeter_sync_role | Admin |
| `00_Grant_Superuser.sql` | Make lakemeter_sync_role a superuser | Admin |
| `01_Create_Tables.py` | Create tables (will own them if run as role) | lakemeter_sync_role |

---

## 🎉 After Fixing

Once ownership is correct, you can:

✅ Run `01_Create_Tables.py` (will drop & recreate)  
✅ Run `02_Create_Views.py` (will drop & recreate)  
✅ Run `04_Add_Sync_Constraints.py`  
✅ Re-run any notebook safely (idempotent)

---

**Created:** 2025-12-13  
**Version:** 1.0

