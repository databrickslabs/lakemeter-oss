# Databricks Apps Deployment Plan

## **What is Databricks Apps?**
- Deploy FastAPI/Flask apps directly on Databricks
- Serverless compute (no infrastructure management)
- Direct access to Lakebase (same network)
- Simple deployment via `databricks apps` CLI

---

## **Project Structure**

```
api_backend/
├── app.yaml              # Databricks App config
├── app.py               # FastAPI app
├── requirements.txt     # Python dependencies
└── README.md
```

---

## **1. app.py (FastAPI App)**

```python
from fastapi import FastAPI, Query
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Lakemeter API", version="1.0.0")

# Database connection from env vars
def get_connection():
    return psycopg2.connect(
        host=os.getenv("LAKEBASE_HOST"),
        port=os.getenv("LAKEBASE_PORT"),
        database=os.getenv("LAKEBASE_DB"),
        user=os.getenv("LAKEBASE_USER"),
        password=os.getenv("LAKEBASE_PASSWORD")
    )

@app.get("/")
def root():
    return {"message": "Lakemeter API", "version": "1.0.0"}

@app.get("/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/v1/regions")
def get_regions(cloud: str = Query(None)):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        if cloud:
            # Single cloud
            query = """
            SELECT DISTINCT region_code, region_name
            FROM lakemeter.sync_ref_sku_region_map
            WHERE cloud = %s
            ORDER BY region_name
            """
            cursor.execute(query, (cloud.upper(),))
            results = cursor.fetchall()
            
            return {
                "success": True,
                "data": {
                    "cloud": cloud.upper(),
                    "count": len(results),
                    "regions": [
                        {"value": r["region_code"], "label": r["region_name"]}
                        for r in results
                    ]
                }
            }
        else:
            # All clouds
            query = """
            SELECT DISTINCT cloud, region_code, region_name
            FROM lakemeter.sync_ref_sku_region_map
            ORDER BY cloud, region_name
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Group by cloud
            by_cloud = {}
            for r in results:
                if r["cloud"] not in by_cloud:
                    by_cloud[r["cloud"]] = []
                by_cloud[r["cloud"]].append({
                    "value": r["region_code"],
                    "label": r["region_name"]
                })
            
            return {
                "success": True,
                "data": by_cloud
            }
    except Exception as e:
        return {
            "success": False,
            "error": {"message": str(e)}
        }
    finally:
        cursor.close()
        conn.close()
```

---

## **2. app.yaml (Databricks App Config)**

```yaml
command: ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

env:
  - name: LAKEBASE_HOST
    value: "instance-364041a4-0aae-44df-bbc6-37ac84169dfe.database.cloud.databricks.com"
  - name: LAKEBASE_PORT
    value: "5432"
  - name: LAKEBASE_DB
    value: "lakemeter_pricing"
  - name: LAKEBASE_USER
    value: "lakemeter_sync"
  - name: LAKEBASE_PASSWORD
    value: "***REMOVED_DATABASE_CREDENTIAL***"

resources:
  cpu: "1"
  memory: "2Gi"
```

---

## **3. requirements.txt**

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.9
```

---

## **Deployment Steps**

### **Step 1: Create Project Folder**

```bash
cd /Users/steven.tan/.cursor/worktrees/Ent_1_-_Q4_FY_2026_Team_Project/vpn
mkdir -p api_backend
cd api_backend
```

### **Step 2: Create Files**

Create `app.py`, `app.yaml`, `requirements.txt`

### **Step 3: Deploy to Databricks**

```bash
databricks apps create lakemeter-api \
  --profile lakemeter \
  --source-code-path .
```

### **Step 4: Get App URL**

```bash
databricks apps get lakemeter-api --profile lakemeter
```

Will return URL like:
```
https://lakemeter-api.apps.cloud.databricks.com
```

### **Step 5: Test API**

```bash
# Test health
curl https://lakemeter-api.apps.cloud.databricks.com/health

# Test regions API
curl https://lakemeter-api.apps.cloud.databricks.com/api/v1/regions?cloud=AWS
```

---

## **Benefits of Databricks Apps**

✅ **No infrastructure** - Serverless, auto-scaling  
✅ **Direct Lakebase access** - Same network, low latency  
✅ **Environment variables** - Secure credential management  
✅ **Auto docs** - FastAPI generates `/docs` (Swagger UI)  
✅ **Easy updates** - Just redeploy  

---

## **Next Steps**

1. Create `api_backend/` folder
2. Create 3 files (app.py, app.yaml, requirements.txt)
3. Deploy with `databricks apps create`
4. Test `/health` and `/api/v1/regions`

**Ready to create the files?** 🚀

