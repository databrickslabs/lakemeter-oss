"""Workload Type API routes."""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RefWorkloadType
from app.schemas import WorkloadTypeResponse

router = APIRouter(prefix="/workload-types", tags=["workload-types"])

# Default workload types based on the CSV reference
DEFAULT_WORKLOAD_TYPES = [
    {
        "workload_type": "JOBS",
        "display_name": "Lakeflow Jobs",
        "description": "Scheduled batch jobs (Classic or Serverless)",
        "show_compute_config": True,
        "show_serverless_toggle": True,
        "show_serverless_performance_mode": True,
        "show_photon_toggle": True,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": True,
        "show_usage_hours": False,
        "show_usage_runs": True,
        "show_usage_tokens": False,
        "sku_product_type_standard": "JOBS_COMPUTE",
        "sku_product_type_photon": "JOBS_COMPUTE_(PHOTON)",
        "sku_product_type_serverless": "JOBS_SERVERLESS_COMPUTE",
        "display_order": 1
    },
    {
        "workload_type": "ALL_PURPOSE",
        "display_name": "All-Purpose Compute",
        "description": "Interactive clusters for notebooks (Classic or Serverless)",
        "show_compute_config": True,
        "show_serverless_toggle": True,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": True,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": True,
        "show_usage_hours": False,
        "show_usage_runs": True,
        "show_usage_tokens": False,
        "sku_product_type_standard": "ALL_PURPOSE_COMPUTE",
        "sku_product_type_photon": "ALL_PURPOSE_COMPUTE_(PHOTON)",
        "sku_product_type_serverless": "INTERACTIVE_SERVERLESS_COMPUTE",
        "display_order": 2
    },
    {
        "workload_type": "DLT",
        "display_name": "Lakeflow Spark Declarative Pipelines",
        "description": "Spark Declarative Pipelines (Classic or Serverless)",
        "show_compute_config": True,
        "show_serverless_toggle": True,
        "show_serverless_performance_mode": True,
        "show_photon_toggle": True,
        "show_dlt_config": True,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": True,
        "show_usage_hours": False,
        "show_usage_runs": True,
        "show_usage_tokens": False,
        "sku_product_type_standard": "DLT_CORE_COMPUTE",
        "sku_product_type_photon": "DLT_CORE_COMPUTE_(PHOTON)",
        "sku_product_type_serverless": "DELTA_LIVE_TABLES_SERVERLESS",
        "display_order": 3
    },
    {
        "workload_type": "DBSQL",
        "display_name": "Databricks SQL",
        "description": "SQL analytics warehouse (Classic/Pro/Serverless)",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": True,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": True,
        "show_usage_runs": True,
        "show_usage_tokens": False,
        "sku_product_type_standard": "SQL_COMPUTE",
        "sku_product_type_photon": "SQL_PRO_COMPUTE",
        "sku_product_type_serverless": "SERVERLESS_SQL_COMPUTE",
        "display_order": 4
    },
    {
        "workload_type": "VECTOR_SEARCH",
        "display_name": "Vector Search",
        "description": "Vector search endpoints for RAG",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": True,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": True,
        "show_vm_pricing": False,
        "show_usage_hours": True,
        "show_usage_runs": False,
        "show_usage_tokens": False,
        "sku_product_type_standard": None,
        "sku_product_type_photon": None,
        "sku_product_type_serverless": "VECTOR_SEARCH_ENDPOINT",
        "display_order": 5
    },
    {
        "workload_type": "MODEL_SERVING",
        "display_name": "Model Serving",
        "description": "Real-time model inference endpoints",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": True,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": True,
        "show_usage_runs": False,
        "show_usage_tokens": False,
        "sku_product_type_standard": None,
        "sku_product_type_photon": None,
        "sku_product_type_serverless": "SERVERLESS_REAL_TIME_INFERENCE",
        "display_order": 6
    },
    {
        "workload_type": "FMAPI_DATABRICKS",
        "display_name": "Foundation Models (Databricks)",
        "description": "Databricks-hosted LLMs (Llama, DBRX)",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": True,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": False,
        "show_usage_runs": False,
        "show_usage_tokens": True,
        "sku_product_type_standard": None,
        "sku_product_type_photon": None,
        "sku_product_type_serverless": "SERVERLESS_REAL_TIME_INFERENCE",
        "display_order": 7
    },
    {
        "workload_type": "FMAPI_PROPRIETARY",
        "display_name": "Foundation Models (Proprietary)",
        "description": "OpenAI, Anthropic, Google models served by Databricks",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": True,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": False,
        "show_usage_runs": False,
        "show_usage_tokens": True,
        "sku_product_type_standard": None,
        "sku_product_type_photon": None,
        "sku_product_type_serverless": None,
        "display_order": 8
    },
    {
        "workload_type": "LAKEBASE",
        "display_name": "Lakebase",
        "description": "Managed PostgreSQL database for operational workloads",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": True,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": True,
        "show_usage_runs": True,
        "show_usage_tokens": False,
        "sku_product_type_standard": None,
        "sku_product_type_photon": None,
        "sku_product_type_serverless": "DATABASE_SERVERLESS_COMPUTE",
        "display_order": 9
    },
    {
        "workload_type": "DATABRICKS_APPS",
        "display_name": "Databricks Apps",
        "description": "Managed app hosting on Databricks",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": True,
        "show_usage_runs": False,
        "show_usage_tokens": False,
        "sku_product_type_standard": "ALL_PURPOSE_SERVERLESS_COMPUTE",
        "sku_product_type_photon": None,
        "sku_product_type_serverless": None,
        "display_order": 10
    },
    {
        "workload_type": "AI_PARSE",
        "display_name": "AI Parse (Document AI)",
        "description": "Document parsing and extraction with AI",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": False,
        "show_usage_runs": False,
        "show_usage_tokens": False,
        "sku_product_type_standard": "SERVERLESS_REAL_TIME_INFERENCE",
        "sku_product_type_photon": None,
        "sku_product_type_serverless": None,
        "display_order": 11
    },
    {
        "workload_type": "SHUTTERSTOCK_IMAGEAI",
        "display_name": "Shutterstock ImageAI",
        "description": "AI image generation via Shutterstock",
        "show_compute_config": False,
        "show_serverless_toggle": False,
        "show_serverless_performance_mode": False,
        "show_photon_toggle": False,
        "show_dlt_config": False,
        "show_dbsql_config": False,
        "show_serverless_product": False,
        "show_fmapi_config": False,
        "show_lakebase_config": False,
        "show_vector_search_mode": False,
        "show_vm_pricing": False,
        "show_usage_hours": False,
        "show_usage_runs": False,
        "show_usage_tokens": False,
        "sku_product_type_standard": "SERVERLESS_REAL_TIME_INFERENCE",
        "sku_product_type_photon": None,
        "sku_product_type_serverless": None,
        "display_order": 12
    }
]


@router.get("", response_model=List[WorkloadTypeResponse])
@router.get("/", response_model=List[WorkloadTypeResponse])
def list_workload_types(
    db: Session = Depends(get_db)
):
    """List all workload types - always use defaults to ensure correct configuration.
    
    Note: We always use DEFAULT_WORKLOAD_TYPES to ensure the latest configuration
    (like show_usage_runs) is applied. Database records may have stale values.
    """
    # Always return the curated default workload types
    # This ensures show_usage_runs and other flags are correct
    return [WorkloadTypeResponse(**wt) for wt in DEFAULT_WORKLOAD_TYPES]


@router.get("/{workload_type}", response_model=WorkloadTypeResponse)
def get_workload_type(
    workload_type: str,
    db: Session = Depends(get_db)
):
    """Get a workload type by key."""
    try:
        wt = db.query(RefWorkloadType).filter(
            RefWorkloadType.workload_type == workload_type
        ).first()
        
        if wt:
            return wt
    except Exception:
        pass
    
    # Find in defaults
    for default_wt in DEFAULT_WORKLOAD_TYPES:
        if default_wt["workload_type"] == workload_type:
            return WorkloadTypeResponse(**default_wt)
    
    # Return a basic default
    return WorkloadTypeResponse(
        workload_type=workload_type,
        display_name=workload_type.replace("_", " ").title(),
        show_compute_config=True,
        show_usage_hours=True
    )
