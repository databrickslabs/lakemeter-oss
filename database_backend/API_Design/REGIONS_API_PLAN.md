# Regions API - Simple Plan

## **Endpoint:**
```
GET /api/v1/regions?cloud=AWS
```

## **Parameters:**
- `cloud` (required): AWS, AZURE, GCP
- `tier` (optional): STANDARD, PREMIUM, ENTERPRISE

## **SQL Query:**

```sql
SELECT DISTINCT
    region_code,
    region_name,
    tier
FROM lakemeter.sync_ref_sku_region_map
WHERE cloud = :cloud
  AND (:tier IS NULL OR tier = :tier)
ORDER BY region_name;
```

## **Response:**

```json
{
  "success": true,
  "data": {
    "cloud": "AWS",
    "tier": "PREMIUM",
    "count": 20,
    "regions": [
      {
        "value": "us-east-1",
        "label": "US East (N. Virginia)"
      },
      {
        "value": "us-west-2",
        "label": "US West (Oregon)"
      },
      {
        "value": "eu-west-1",
        "label": "Europe (Ireland)"
      }
    ]
  }
}
```

## **All Clouds at Once:**

```
GET /api/v1/regions
```

**Response:**

```json
{
  "success": true,
  "data": {
    "AWS": [
      {"value": "us-east-1", "label": "US East (N. Virginia)"},
      {"value": "us-west-2", "label": "US West (Oregon)"}
    ],
    "AZURE": [
      {"value": "eastus", "label": "East US"},
      {"value": "westus", "label": "West US"}
    ],
    "GCP": [
      {"value": "us-central1", "label": "Iowa"},
      {"value": "us-east1", "label": "South Carolina"}
    ]
  }
}
```

## **Python Implementation:**

```python
@router.get("/api/v1/regions")
async def get_regions(cloud: str = None, tier: str = None):
    if cloud:
        # Single cloud
        query = """
        SELECT DISTINCT region_code, region_name
        FROM sync_ref_sku_region_map
        WHERE cloud = %s AND (%s IS NULL OR tier = %s)
        ORDER BY region_name
        """
        results = execute_query(query, (cloud, tier, tier))
        
        return {
            "success": True,
            "data": {
                "cloud": cloud,
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
        FROM sync_ref_sku_region_map
        ORDER BY cloud, region_name
        """
        results = execute_query(query)
        
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
```

**Done!**


