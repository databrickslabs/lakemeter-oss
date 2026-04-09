# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: DBSQL Classic Warehouse
# MAGIC 
# MAGIC **DBSQL Characteristics:**
# MAGIC - **Warehouse sizes:** 2X-Small, X-Small, Small, Medium, Large, X-Large, 2X-Large, 3X-Large, 4X-Large
# MAGIC - **Num clusters:** 1-10 (multiple clusters for scaling)
# MAGIC - **Product type:** SQL_COMPUTE
# MAGIC - **No Photon** (Classic warehouse)

# COMMAND ----------

%pip install psycopg2-binary pandas tabulate

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import psycopg2, pandas as pd, uuid
from datetime import datetime
from tabulate import tabulate

LAKEBASE_HOST = "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
LAKEBASE_PORT = 5432
LAKEBASE_DB = "lakemeter_pricing"
LAKEBASE_USER = "lakemeter_sync_role"
LAKEBASE_PASSWORD = dbutils.secrets.get(scope="lakemeter-credentials", key="lakebase-password")

def get_connection():
    return psycopg2.connect(host=LAKEBASE_HOST, port=LAKEBASE_PORT, database=LAKEBASE_DB, user=LAKEBASE_USER, password=LAKEBASE_PASSWORD)

def execute_query(query, params=None, fetch=True):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                columns = [desc[0] for desc in cur.description] if cur.description else []
                results = cur.fetchall()
                conn.commit()
                return pd.DataFrame(results, columns=columns) if results else pd.DataFrame()
            else:
                conn.commit()
                return None
    finally:
        conn.close()

print("✅ Setup complete!")

# COMMAND ----------

# Create test user
TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())
execute_query("INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
              (TEST_USER_ID, f'test_dbsql_classic_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

# Get regions
available_regions_df = execute_query("SELECT DISTINCT cloud, region_code FROM lakemeter.sync_ref_sku_region_map WHERE (cloud = 'AWS' AND region_code LIKE 'us-east-%') OR (cloud = 'AZURE' AND region_code = 'eastus') OR (cloud = 'GCP' AND region_code LIKE 'us-central%') ORDER BY cloud, region_code;")
region_map = {}
for cloud in ['AWS', 'AZURE', 'GCP']:
    cloud_regions = available_regions_df[available_regions_df['cloud'] == cloud]
    if len(cloud_regions) >= 1:
        region_map[cloud] = cloud_regions.iloc[0]['region_code']

print("✅ Test data loaded")

# COMMAND ----------

# Define scenarios
test_scenarios = []
scenario_id = 1
warehouse_sizes = ['X-Small', 'Small', 'Medium', 'Large']
num_clusters_options = [1, 2, 4]
usage_patterns = [{'runs': 8, 'mins': 60}, {'runs': 24, 'mins': 60}]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
        for size in warehouse_sizes:
            for num_clusters in num_clusters_options:
                for usage in usage_patterns:
                    region = region_map[cloud]
                    test_scenarios.append({
                        'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                        'workload_name': f"{cloud} {tier} {size} {num_clusters}clusters {usage['runs']}h",
                        'dbsql_warehouse_type': 'CLASSIC', 'dbsql_warehouse_size': size, 'dbsql_num_clusters': num_clusters,
                        'runs_per_day': usage['runs'], 'avg_runtime_minutes': usage['mins'], 'days_per_month': 30,
                        'notes': f"DBSQL Classic {size} {num_clusters} clusters"
                    })
                    scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} scenarios")

# COMMAND ----------

# Create estimates
unique_combos = {f"{s['cloud']}_{s['region']}_{s['tier']}": {'cloud': s['cloud'], 'region': s['region'], 'tier': s['tier']} for s in test_scenarios}
estimate_map = {}
for key, combo in unique_combos.items():
    estimate_id = str(uuid.uuid4())
    estimate_map[key] = estimate_id
    execute_query("INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                  (estimate_id, TEST_USER_ID, f"Test: {combo[\'cloud\']} {combo[\'region\']} {combo[\'tier\']}", combo[\'cloud\'], combo['region'], combo['tier'], datetime.now(), datetime.now()), fetch=False)

print(f"✅ Created {len(estimate_map)} estimates")

# COMMAND ----------

# Insert line items
line_item_ids = []
for scenario in test_scenarios:
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, dbsql_warehouse_type, dbsql_warehouse_size, dbsql_num_clusters, runs_per_day, avg_runtime_minutes, days_per_month, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'DBSQL', False, scenario['dbsql_warehouse_type'], scenario['dbsql_warehouse_size'], scenario['dbsql_num_clusters'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], scenario['notes'], datetime.now(), datetime.now()), fetch=False)

print(f"✅ Inserted {len(line_item_ids)} line items")

# COMMAND ----------

# Query results
results_df = execute_query("SELECT c.workload_name, c.cloud, c.tier, c.dbsql_warehouse_type, c.dbsql_warehouse_size, c.dbsql_num_clusters, c.hours_per_month, c.dbu_per_hour, c.price_per_dbu, c.dbu_cost_per_month, c.cost_per_month FROM lakemeter.v_line_items_with_costs c WHERE c.line_item_id = ANY(%s::uuid[]) ORDER BY c.display_order;", (line_item_ids,))

for col in ['dbsql_num_clusters', 'hours_per_month', 'dbu_per_hour', 'price_per_dbu', 'dbu_cost_per_month', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

print(f"✅ Retrieved {len(results_df)} results")

# COMMAND ----------

# Display
results_df['dbu_per_hour'] = results_df['dbu_per_hour'].round(4)
results_df['price_per_dbu'] = results_df['price_per_dbu'].round(6)
results_df['cost_per_month'] = results_df['cost_per_month'].round(2)

print("=" * 180)
print("DBSQL CLASSIC - COST CALCULATION SUMMARY")
print("=" * 180)
print(tabulate(results_df.head(20), headers='keys', tablefmt='grid', showindex=False, maxcolwidths=30))
display(results_df)

# COMMAND ----------

# Validation
assert len(results_df) == len(test_scenarios), "❌ Missing scenarios"
assert (results_df['cost_per_month'] > 0).all(), "❌ Some costs $0"
print(f"✅ All {len(test_scenarios)} DBSQL Classic scenarios validated!")

# COMMAND ----------
