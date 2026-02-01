# Databricks notebook source
# MAGIC %md
# MAGIC # Test Case: DBSQL Pro Warehouse
# MAGIC 
# MAGIC **DBSQL Pro Characteristics:**
# MAGIC - **Product type:** SQL_PRO_COMPUTE
# MAGIC - **Enhanced performance** vs Classic
# MAGIC - **Same warehouse sizes** as Classic

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

TEST_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_USER_ID = str(uuid.uuid4())
execute_query("INSERT INTO lakemeter.users (user_id, full_name, email, role, is_active, created_at) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
              (TEST_USER_ID, f'test_dbsql_pro_{TEST_RUN_ID}', f'test_{TEST_RUN_ID}@databricks.com', 'admin', True, datetime.now()), fetch=False)

available_regions_df = execute_query("SELECT DISTINCT cloud, region_code FROM lakemeter.sync_ref_sku_region_map WHERE (cloud = 'AWS' AND region_code LIKE 'us-east-%') OR (cloud = 'AZURE' AND region_code = 'eastus') OR (cloud = 'GCP' AND region_code LIKE 'us-central%') ORDER BY cloud, region_code;")
region_map = {cloud: available_regions_df[available_regions_df['cloud'] == cloud].iloc[0]['region_code'] for cloud in ['AWS', 'AZURE', 'GCP'] if len(available_regions_df[available_regions_df['cloud'] == cloud]) >= 1}

print("✅ Test data loaded")

# COMMAND ----------

test_scenarios = []
scenario_id = 1
warehouse_sizes = ['Small', 'Medium', 'Large']
num_clusters_options = [1, 2]

for cloud in ['AWS', 'AZURE', 'GCP']:
    for tier in ['STANDARD', 'PREMIUM', 'ENTERPRISE']:
        if cloud == 'AZURE' and tier == 'ENTERPRISE':
            continue
        for size in warehouse_sizes:
            for num_clusters in num_clusters_options:
                region = region_map[cloud]
                test_scenarios.append({
                    'scenario_id': scenario_id, 'cloud': cloud, 'region': region, 'tier': tier,
                    'workload_name': f"{cloud} {tier} {size} {num_clusters}clusters PRO",
                    'dbsql_warehouse_type': 'PRO', 'dbsql_warehouse_size': size, 'dbsql_num_clusters': num_clusters,
                    'runs_per_day': 12, 'avg_runtime_minutes': 60, 'days_per_month': 30,
                    'notes': f"DBSQL Pro {size}"
                })
                scenario_id += 1

print(f"✅ Generated {len(test_scenarios)} scenarios")

# COMMAND ----------

unique_combos = {f"{s['cloud']}_{s['region']}_{s['tier']}": {'cloud': s['cloud'], 'region': s['region'], 'tier': s['tier']} for s in test_scenarios}
estimate_map = {}
for key, combo in unique_combos.items():
    estimate_id = str(uuid.uuid4())
    estimate_map[key] = estimate_id
    execute_query("INSERT INTO lakemeter.estimates (estimate_id, owner_user_id, estimate_name, cloud, region, tier, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                  (estimate_id, TEST_USER_ID, f"Test: {combo[\'cloud\']} {combo[\'region\']} {combo[\'tier\']}", combo[\'cloud\'], combo['region'], combo['tier'], datetime.now(), datetime.now()), fetch=False)

line_item_ids = []
for scenario in test_scenarios:
    line_item_id = str(uuid.uuid4())
    line_item_ids.append(line_item_id)
    estimate_key = f"{scenario['cloud']}_{scenario['region']}_{scenario['tier']}"
    execute_query("""INSERT INTO lakemeter.line_items (line_item_id, estimate_id, display_order, workload_name, workload_type, serverless_enabled, dbsql_warehouse_type, dbsql_warehouse_size, dbsql_num_clusters, runs_per_day, avg_runtime_minutes, days_per_month, notes, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                  (line_item_id, estimate_map[estimate_key], scenario['scenario_id'], scenario['workload_name'], 'DBSQL', False, 'PRO', scenario['dbsql_warehouse_size'], scenario['dbsql_num_clusters'], scenario['runs_per_day'], scenario['avg_runtime_minutes'], scenario['days_per_month'], scenario['notes'], datetime.now(), datetime.now()), fetch=False)

print(f"✅ Created {len(estimate_map)} estimates, {len(line_item_ids)} line items")

# COMMAND ----------

results_df = execute_query("SELECT c.workload_name, c.cloud, c.tier, c.dbsql_warehouse_type, c.dbsql_warehouse_size, c.dbsql_num_clusters, c.dbu_per_hour, c.price_per_dbu, c.cost_per_month FROM lakemeter.v_line_items_with_costs c WHERE c.line_item_id = ANY(%s::uuid[]) ORDER BY c.display_order;", (line_item_ids,))

for col in ['dbsql_num_clusters', 'dbu_per_hour', 'price_per_dbu', 'cost_per_month']:
    if col in results_df.columns:
        results_df[col] = pd.to_numeric(results_df[col], errors='coerce')

results_df['cost_per_month'] = results_df['cost_per_month'].round(2)
print("=" * 150)
print("DBSQL PRO - COST CALCULATION SUMMARY")
print("=" * 150)
print(tabulate(results_df.head(20), headers='keys', tablefmt='grid', showindex=False))
display(results_df)

assert len(results_df) == len(test_scenarios) and (results_df['cost_per_month'] > 0).all()
print(f"✅ All {len(test_scenarios)} DBSQL Pro scenarios validated!")

# COMMAND ----------
