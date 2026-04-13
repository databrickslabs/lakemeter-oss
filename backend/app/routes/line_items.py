"""Line Item API routes."""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.database import get_db
from app.models import LineItem, Estimate, User
from app.models.sharing import Sharing
from app.schemas import LineItemCreate, LineItemUpdate, LineItemResponse
from app.auth import get_current_user

# ---- Case normalization for enum-like string fields ----
_UPPERCASE_FIELDS = {'cloud', 'dbsql_warehouse_type', 'dlt_edition', 'workload_type'}
_LOWERCASE_FIELDS = {
    'serverless_mode', 'vector_search_mode', 'fmapi_provider',
    'fmapi_rate_type', 'fmapi_endpoint_type', 'fmapi_context_length',
    'model_serving_gpu_type', 'driver_pricing_tier', 'worker_pricing_tier',
    'dbsql_vm_pricing_tier',
}


def _normalize_case(data: dict) -> dict:
    """Normalize enum-like string fields to canonical case."""
    for field in _UPPERCASE_FIELDS:
        if field in data and isinstance(data[field], str):
            data[field] = data[field].upper()
    for field in _LOWERCASE_FIELDS:
        if field in data and isinstance(data[field], str):
            data[field] = data[field].lower()
    return data


def _touch_estimate(estimate_id: UUID, db: Session):
    """Update the estimate's updated_at timestamp."""
    estimate = db.query(Estimate).filter(Estimate.estimate_id == estimate_id).first()
    if estimate:
        estimate.updated_at = datetime.utcnow()
        db.add(estimate)


class CloneRequest(BaseModel):
    new_name: Optional[str] = None

router = APIRouter(prefix="/line-items", tags=["line-items"])


def _check_estimate_access(
    estimate_id: UUID,
    user: User,
    db: Session,
    require_edit: bool = False
) -> Estimate:
    """
    Check if user has access to an estimate.
    
    Args:
        estimate_id: The estimate UUID
        user: The current user
        db: Database session
        require_edit: If True, user must have edit permission
    
    Returns:
        Estimate object
    
    Raises:
        HTTPException if no access
    """
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Check ownership
    is_owner = estimate.owner_user_id == user.user_id
    
    if is_owner:
        return estimate
    
    # Check if shared with user
    sharing = db.query(Sharing).filter(
        Sharing.estimate_id == estimate_id,
        Sharing.shared_with_user_id == user.user_id
    ).first()
    
    if not sharing:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    if require_edit and sharing.permission != "edit":
        raise HTTPException(status_code=403, detail="You don't have edit permission for this estimate")
    
    return estimate


@router.get("/estimate/{estimate_id}", response_model=List[LineItemResponse])
def list_line_items(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all line items for an estimate the user has access to."""
    _check_estimate_access(estimate_id, current_user, db)
    
    items = db.query(LineItem).filter(
        LineItem.estimate_id == estimate_id
    ).order_by(LineItem.display_order).all()
    
    return items


@router.post("/", response_model=LineItemResponse, status_code=201)
def create_line_item(
    line_item: LineItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new line item. User must have edit access to the estimate."""
    _check_estimate_access(line_item.estimate_id, current_user, db, require_edit=True)
    
    # Get max display order
    max_order = db.query(LineItem).filter(
        LineItem.estimate_id == line_item.estimate_id
    ).count()
    
    item_data = _normalize_case(line_item.model_dump())
    db_item = LineItem(**item_data)
    if db_item.display_order == 0:
        db_item.display_order = max_order
    
    db.add(db_item)
    _touch_estimate(line_item.estimate_id, db)  # Update estimate timestamp
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/{line_item_id}", response_model=LineItemResponse)
def get_line_item(
    line_item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a line item by ID if user has access to its estimate."""
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    _check_estimate_access(item.estimate_id, current_user, db)
    
    return item


@router.put("/{line_item_id}", response_model=LineItemResponse)
def update_line_item(
    line_item_id: UUID,
    line_item_update: LineItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a line item. User must have edit access to the estimate."""
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    _check_estimate_access(item.estimate_id, current_user, db, require_edit=True)
    
    update_data = _normalize_case(line_item_update.model_dump(exclude_unset=True))
    for field, value in update_data.items():
        setattr(item, field, value)

    _touch_estimate(item.estimate_id, db)  # Update estimate timestamp
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{line_item_id}", status_code=204)
def delete_line_item(
    line_item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a line item. User must have edit access to the estimate."""
    item = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    _check_estimate_access(item.estimate_id, current_user, db, require_edit=True)
    
    estimate_id = item.estimate_id  # Store before delete
    db.delete(item)
    _touch_estimate(estimate_id, db)  # Update estimate timestamp
    db.commit()


@router.post("/reorder", status_code=200)
def reorder_line_items(
    estimate_id: UUID,
    item_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reorder line items. User must have edit access to the estimate."""
    _check_estimate_access(estimate_id, current_user, db, require_edit=True)
    
    for index, item_id in enumerate(item_ids):
        item = db.query(LineItem).filter(
            LineItem.line_item_id == item_id,
            LineItem.estimate_id == estimate_id
        ).first()
        
        if item:
            item.display_order = index
    
    _touch_estimate(estimate_id, db)  # Update estimate timestamp
    db.commit()
    return {"message": "Line items reordered successfully"}


@router.post("/{line_item_id}/clone", response_model=LineItemResponse, status_code=201)
def clone_line_item(
    line_item_id: UUID,
    payload: Optional[CloneRequest] = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clone a line item (workload). User must have edit access to the estimate.
    
    Optionally provide a new_name in the request body.
    """
    # Get the original line item
    original = db.query(LineItem).filter(
        LineItem.line_item_id == line_item_id
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Line item not found")
    
    # Check edit access to the estimate
    _check_estimate_access(original.estimate_id, current_user, db, require_edit=True)
    
    # Get new name from payload or generate from original
    new_name = payload.new_name if payload and payload.new_name else f"{original.workload_name} (Copy)"
    
    # Get max display order in the estimate
    max_order = db.query(LineItem).filter(
        LineItem.estimate_id == original.estimate_id
    ).count()
    
    # Create the cloned line item - only copy fields that exist in the model
    cloned = LineItem(
        estimate_id=original.estimate_id,
        display_order=max_order,
        workload_name=new_name,
        workload_type=original.workload_type,
        cloud=original.cloud,
        # Serverless
        serverless_enabled=original.serverless_enabled,
        serverless_mode=original.serverless_mode,
        # Classic Compute
        photon_enabled=original.photon_enabled,
        driver_node_type=original.driver_node_type,
        worker_node_type=original.worker_node_type,
        num_workers=original.num_workers,
        # DLT
        dlt_edition=original.dlt_edition,
        # DBSQL
        dbsql_warehouse_type=original.dbsql_warehouse_type,
        dbsql_warehouse_size=original.dbsql_warehouse_size,
        dbsql_num_clusters=original.dbsql_num_clusters,
        dbsql_vm_pricing_tier=original.dbsql_vm_pricing_tier,
        dbsql_vm_payment_option=original.dbsql_vm_payment_option,
        # Vector Search
        vector_search_mode=original.vector_search_mode,
        vector_capacity_millions=original.vector_capacity_millions,
        vector_search_storage_gb=original.vector_search_storage_gb,
        # Model Serving
        model_serving_gpu_type=original.model_serving_gpu_type,
        # FMAPI
        fmapi_provider=original.fmapi_provider,
        fmapi_model=original.fmapi_model,
        fmapi_endpoint_type=original.fmapi_endpoint_type,
        fmapi_context_length=original.fmapi_context_length,
        fmapi_rate_type=original.fmapi_rate_type,
        fmapi_quantity=original.fmapi_quantity,
        # Lakebase
        lakebase_cu=original.lakebase_cu,
        lakebase_storage_gb=original.lakebase_storage_gb,
        lakebase_ha_nodes=original.lakebase_ha_nodes,
        lakebase_backup_retention_days=original.lakebase_backup_retention_days,
        # Usage
        runs_per_day=original.runs_per_day,
        avg_runtime_minutes=original.avg_runtime_minutes,
        days_per_month=original.days_per_month,
        hours_per_month=original.hours_per_month,
        # Pricing
        driver_pricing_tier=original.driver_pricing_tier,
        worker_pricing_tier=original.worker_pricing_tier,
        driver_payment_option=original.driver_payment_option,
        worker_payment_option=original.worker_payment_option,
        # Additional
        workload_config=original.workload_config,
        notes=original.notes
    )
    
    db.add(cloned)
    _touch_estimate(original.estimate_id, db)  # Update estimate timestamp
    db.commit()
    db.refresh(cloned)
    
    return cloned
