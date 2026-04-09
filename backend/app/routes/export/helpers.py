"""Access control and display helper functions for export."""
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Estimate, User
from app.models.sharing import Sharing


def _check_estimate_access(estimate_id: UUID, user: User, db: Session) -> Estimate:
    """Check if user has access to an estimate."""
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    is_owner = estimate.owner_user_id == user.user_id
    is_shared = db.query(Sharing).filter(
        Sharing.estimate_id == estimate_id,
        Sharing.shared_with_user_id == user.user_id
    ).first() is not None
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return estimate


def _get_workload_display_name(workload_type: str) -> str:
    """Get friendly display name for workload type."""
    names = {
        'JOBS': 'Lakeflow Job Compute',
        'ALL_PURPOSE': 'All-Purpose Compute',
        'DLT': 'Lakeflow Spark Declarative Pipelines',
        'DBSQL': 'Databricks SQL',
        'VECTOR_SEARCH': 'Vector Search',
        'MODEL_SERVING': 'Model Serving',
        'FMAPI_DATABRICKS': 'Foundation Models (Databricks)',
        'FMAPI_PROPRIETARY': 'Foundation Models (Proprietary)',
        'LAKEBASE': 'Lakebase',
        'DATABRICKS_APPS': 'Databricks Apps',
        'CLEAN_ROOM': 'Clean Room',
        'AI_PARSE': 'AI Parse (Document AI)',
        'SHUTTERSTOCK_IMAGEAI': 'Shutterstock ImageAI',
        'LAKEFLOW_CONNECT': 'Lakeflow Connect',
    }
    return names.get(workload_type, workload_type)


def _get_workload_config_details(item) -> str:
    """Get workload-specific configuration details for display."""
    wt = item.workload_type or ''
    details = []

    if wt in ('JOBS', 'ALL_PURPOSE', 'DLT') and item.serverless_enabled:
        serverless_mode = (item.serverless_mode or 'standard').capitalize()
        details.append(f"Mode: {serverless_mode}")

    if wt == 'DBSQL':
        details.extend(_dbsql_details(item))
    elif wt == 'VECTOR_SEARCH':
        details.extend(_vector_search_details(item))
    elif wt == 'MODEL_SERVING':
        details.extend(_model_serving_details(item))
    elif wt in ('FMAPI_DATABRICKS', 'FMAPI_PROPRIETARY'):
        details.extend(_fmapi_details(item))
    elif wt == 'LAKEBASE':
        details.extend(_lakebase_details(item))
    elif wt == 'DLT':
        details.extend(_dlt_details(item))
    elif wt == 'DATABRICKS_APPS':
        size = (getattr(item, 'databricks_apps_size', None) or 'medium').capitalize()
        details.append(f"Size: {size}")
    elif wt == 'CLEAN_ROOM':
        collaborators = getattr(item, 'clean_room_collaborators', None) or 1
        details.append(f"Collaborators: {collaborators}")
    elif wt == 'AI_PARSE':
        details.extend(_ai_parse_details(item))
    elif wt == 'SHUTTERSTOCK_IMAGEAI':
        images = getattr(item, 'shutterstock_images', None) or 0
        details.append(f"Images/mo: {images:,}")
    elif wt == 'LAKEFLOW_CONNECT':
        details.extend(_lakeflow_connect_details(item))

    return ' | '.join(details) if details else '-'


def _dbsql_details(item) -> list:
    details = []
    if item.dbsql_warehouse_type:
        details.append(f"Type: {item.dbsql_warehouse_type}")
    if item.dbsql_warehouse_size:
        details.append(f"Size: {item.dbsql_warehouse_size}")
    if item.dbsql_num_clusters and item.dbsql_num_clusters > 1:
        details.append(f"Clusters: {item.dbsql_num_clusters}")
    return details


def _vector_search_details(item) -> list:
    details = []
    mode = item.vector_search_mode or 'standard'
    mode_display = 'Storage Optimized' if mode == 'storage_optimized' else 'Standard'
    details.append(f"Mode: {mode_display}")
    if item.vector_capacity_millions:
        details.append(f"Capacity: {item.vector_capacity_millions}M vectors")
    return details


MODEL_SERVING_GPU_NAMES = {
    'cpu': 'CPU',
    'gpu_small_t4': 'Small (T4)',
    'gpu_medium_a10g_1x': 'Medium (A10G 1x)',
    'gpu_medium_a10g_4x': 'Medium (A10G 4x)',
    'gpu_medium_a10g_8x': 'Medium (A10G 8x)',
    'gpu_large_a10g_4x': 'Large (A10G 4x)',
    'gpu_medium_a100_1x': 'Medium (A100 1x)',
    'gpu_large_a100_2x': 'Large (A100 2x)',
    'gpu_xlarge_a100_40gb_8x': 'XLarge (A100 40GB 8x)',
    'gpu_xlarge_a100_80gb_8x': 'XLarge (A100 80GB 8x)',
    'gpu_xlarge_a100_80gb_1x': 'XLarge (A100 80GB 1x)',
    'gpu_2xlarge_a100_80gb_2x': '2XLarge (A100 80GB 2x)',
    'gpu_4xlarge_a100_80gb_4x': '4XLarge (A100 80GB 4x)',
    'gpu_medium_g2_standard_8': 'Medium (G2 Standard 8)',
}


def _model_serving_details(item) -> list:
    details = []
    if item.model_serving_gpu_type:
        name = MODEL_SERVING_GPU_NAMES.get(
            item.model_serving_gpu_type, item.model_serving_gpu_type
        )
        details.append(f"GPU: {name}")
    # Show concurrency (from dedicated column or default 4)
    concurrency = getattr(item, 'model_serving_concurrency', None) or 4
    scale_out = getattr(item, 'model_serving_scale_out', None) or 'small'
    scale_labels = {'small': 'Small', 'medium': 'Medium', 'large': 'Large', 'custom': 'Custom'}
    label = scale_labels.get(scale_out, scale_out)
    details.append(f"Scale-Out: {label} ({concurrency} concurrency)")
    return details


def _fmapi_details(item) -> list:
    details = []
    if item.fmapi_model:
        details.append(f"Model: {item.fmapi_model}")
    if item.fmapi_rate_type:
        rate_type_display = {
            'input_token': 'Input Tokens',
            'output_token': 'Output Tokens',
            'cache_read': 'Cache Read',
            'cache_write': 'Cache Write',
            'batch_inference': 'Batch Inference',
            'provisioned_scaling': 'Provisioned Scaling',
            'provisioned_entry': 'Provisioned Entry',
        }
        details.append(f"Rate: {rate_type_display.get(item.fmapi_rate_type, item.fmapi_rate_type)}")
    if item.fmapi_quantity:
        token_types = ('input_token', 'output_token', 'cache_read', 'cache_write')
        if item.fmapi_rate_type in token_types:
            details.append(f"Tokens: {float(item.fmapi_quantity):.1f}M/mo")
        else:
            details.append(f"Hours: {item.fmapi_quantity}")
    return details


def _lakebase_details(item) -> list:
    details = []
    if item.lakebase_cu:
        details.append(f"CU: {item.lakebase_cu}")
    if item.lakebase_ha_nodes:
        details.append(f"Nodes: {item.lakebase_ha_nodes}")
    return details


def _dlt_details(item) -> list:
    details = []
    if item.dlt_edition:
        details.append(f"Edition: {item.dlt_edition.upper()}")
    if item.photon_enabled:
        details.append("Photon")
    return details


def _ai_parse_details(item) -> list:
    details = []
    mode = getattr(item, 'ai_parse_mode', None) or 'pages'
    if mode == 'dbu':
        details.append("Mode: Direct DBU")
    else:
        complexity_labels = {
            'low_text': 'Low (Text Only)',
            'low_images': 'Low (With Images)',
            'medium': 'Medium',
            'high': 'High',
        }
        complexity = getattr(item, 'ai_parse_complexity', None) or 'medium'
        details.append(f"Complexity: {complexity_labels.get(complexity, complexity)}")
        pages = getattr(item, 'ai_parse_pages_thousands', None) or 0
        details.append(f"Pages: {float(pages):.0f}K")
    return details


def _lakeflow_connect_details(item) -> list:
    details = []
    details.append("Pipeline: DLT Serverless")
    if getattr(item, 'lakeflow_connect_gateway_enabled', False):
        gw_instance = getattr(item, 'lakeflow_connect_gateway_instance', None) or 'default'
        details.append(f"Gateway: {gw_instance}")
    return details


def _get_pricing_tier_display(tier: str) -> str:
    displays = {
        'on_demand': 'On-Demand', 'spot': 'Spot',
        'reserved_1y': '1-Year Reserved', 'reserved_3y': '3-Year Reserved',
    }
    return displays.get(tier, tier or '-')
