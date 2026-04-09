"""Estimates API routes."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, select
from pydantic import BaseModel

from app.database import get_db
from app.models import Estimate, LineItem, User
from app.models.sharing import Sharing
from app.schemas import (
    EstimateCreate,
    EstimateUpdate,
    EstimateResponse,
    EstimateListResponse,
    EstimateWithLineItemsResponse,
    LineItemResponse
)
from app.auth import get_current_user

# ---- Case normalization for estimate-level enum fields ----
_ESTIMATE_UPPER_FIELDS = {'cloud', 'tier'}


def _normalize_estimate_case(data: dict) -> dict:
    """Normalize cloud and tier to canonical UPPERCASE."""
    for field in _ESTIMATE_UPPER_FIELDS:
        if field in data and isinstance(data[field], str):
            data[field] = data[field].upper()
    return data


class CloneRequest(BaseModel):
    new_name: Optional[str] = None


router = APIRouter(prefix="/estimates", tags=["estimates"])


@router.get("", response_model=List[EstimateListResponse])
@router.get("/", response_model=List[EstimateListResponse])
def list_estimates(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in estimate name or customer name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List estimates visible to the current user.
    
    Returns estimates where:
    - User is the owner (owner_user_id)
    - Estimate is shared with the user (via Sharing table)
    """
    # Use a single efficient query with LEFT JOIN to count line items
    # This avoids N+1 query problem
    line_item_count_subquery = (
        db.query(
            LineItem.estimate_id,
            func.count(LineItem.line_item_id).label('line_item_count')
        )
        .group_by(LineItem.estimate_id)
        .subquery()
    )
    
    # Shared estimates subquery - use select() to avoid SAWarning
    shared_estimate_ids = select(Sharing.estimate_id).where(
        Sharing.shared_with_user_id == current_user.user_id
    ).scalar_subquery()
    
    # Main query with join for line item count
    query = (
        db.query(
            Estimate,
            func.coalesce(line_item_count_subquery.c.line_item_count, 0).label('line_item_count')
        )
        .outerjoin(line_item_count_subquery, Estimate.estimate_id == line_item_count_subquery.c.estimate_id)
        .filter(Estimate.is_deleted == False)
        .filter(
            or_(
                Estimate.owner_user_id == current_user.user_id,
                Estimate.estimate_id.in_(shared_estimate_ids)
            )
        )
    )
    
    # Apply additional filters
    if status:
        query = query.filter(Estimate.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Estimate.estimate_name.ilike(search_term),
                Estimate.customer_name.ilike(search_term)
            )
        )
    
    results = query.order_by(Estimate.updated_at.desc()).all()
    
    return [
        EstimateListResponse(
            estimate_id=e.estimate_id,
            estimate_name=e.estimate_name,
            customer_name=e.customer_name,
            cloud=e.cloud,
            region=e.region,
            tier=e.tier,
            status=e.status,
            version=e.version,
            line_item_count=line_count,
            display_order=e.display_order or 0,
            created_at=e.created_at,
            updated_at=e.updated_at
        )
        for e, line_count in results
    ]


@router.post("/", response_model=EstimateResponse, status_code=201)
def create_estimate(
    estimate: EstimateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new estimate owned by the current user."""
    from app.config import log_info, log_error
    
    try:
        log_info(f"Creating estimate '{estimate.estimate_name}' for user {current_user.user_id}")
        
        db_estimate = Estimate(
            **_normalize_estimate_case(estimate.model_dump()),
            owner_user_id=current_user.user_id  # Set the owner
        )
        db.add(db_estimate)
        db.commit()
        db.refresh(db_estimate)
        
        log_info(f"Estimate created successfully: {db_estimate.estimate_id}")
        return db_estimate
    except Exception as e:
        log_error(f"Failed to create estimate: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create estimate: {str(e)}")


# NOTE: This route MUST be defined BEFORE /{estimate_id} routes to avoid "me" being parsed as UUID
@router.get("/me/info")
def get_current_user_info(
    request: Request
):
    """Get the current authenticated user's info from headers (no DB required)."""
    from app.auth.databricks_auth import get_user_from_headers
    
    email, _ = get_user_from_headers(request)
    
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Use email prefix as display name (e.g., "junyi.tiong" from "junyi.tiong@databricks.com")
    display_name = email.split("@")[0].replace(".", " ").title()
    
    return {
        "user_id": email,
        "email": email,
        "full_name": display_name,
        "role": "user"
    }


def _get_estimate_for_user(
    estimate_id: UUID,
    user: User,
    db: Session,
    require_owner: bool = False
) -> Estimate:
    """
    Get an estimate if the user has access to it.
    
    Args:
        estimate_id: The estimate UUID
        user: The current user
        db: Database session
        require_owner: If True, user must be the owner (not just shared)
    
    Returns:
        Estimate object
    
    Raises:
        HTTPException 404 if not found or no access
    """
    estimate = db.query(Estimate).filter(
        Estimate.estimate_id == estimate_id,
        Estimate.is_deleted == False
    ).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    # Check ownership
    is_owner = estimate.owner_user_id == user.user_id
    
    if require_owner and not is_owner:
        raise HTTPException(status_code=403, detail="Only the owner can perform this action")
    
    # Check if shared with user
    is_shared = db.query(Sharing).filter(
        Sharing.estimate_id == estimate_id,
        Sharing.shared_with_user_id == user.user_id
    ).first() is not None
    
    if not is_owner and not is_shared:
        raise HTTPException(status_code=404, detail="Estimate not found")
    
    return estimate


@router.post("/reorder", status_code=200)
def reorder_estimates(
    estimate_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reorder estimates for the current user."""
    for index, eid in enumerate(estimate_ids):
        estimate = db.query(Estimate).filter(
            Estimate.estimate_id == eid,
            Estimate.owner_user_id == current_user.user_id,
            Estimate.is_deleted == False
        ).first()
        if estimate:
            estimate.display_order = index
    db.commit()
    return {"message": "Estimates reordered successfully"}


@router.get("/{estimate_id}", response_model=EstimateResponse)
def get_estimate(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get an estimate by ID if user has access."""
    estimate = _get_estimate_for_user(estimate_id, current_user, db)
    return estimate


@router.get("/{estimate_id}/full")
def get_estimate_with_line_items(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get estimate with all line items in a single optimized query.
    Returns both estimate details and full line items to avoid multiple round trips.
    """
    estimate = _get_estimate_for_user(estimate_id, current_user, db)
    
    # Get full line items in same query context
    line_items = db.query(LineItem).filter(
        LineItem.estimate_id == estimate_id
    ).order_by(LineItem.display_order).all()
    
    return {
        "estimate": EstimateWithLineItemsResponse.model_validate(estimate),
        "line_items": [LineItemResponse.model_validate(item) for item in line_items]
    }


@router.put("/{estimate_id}", response_model=EstimateResponse)
def update_estimate(
    estimate_id: UUID,
    estimate_update: EstimateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an estimate. User must have access (owner or shared with edit permission)."""
    estimate = _get_estimate_for_user(estimate_id, current_user, db)
    
    update_data = _normalize_estimate_case(estimate_update.model_dump(exclude_unset=True))

    # Check if cloud is being changed
    if 'cloud' in update_data and update_data['cloud'] != estimate.cloud:
        # Count existing workloads
        workload_count = db.query(LineItem).filter(
            LineItem.estimate_id == estimate_id
        ).count()
        
        if workload_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change cloud provider. Remove all {workload_count} workload(s) first."
            )
    
    for field, value in update_data.items():
        setattr(estimate, field, value)
    
    estimate.version += 1
    estimate.updated_by = current_user.user_id
    estimate.updated_at = datetime.utcnow()  # Explicitly update timestamp
    db.commit()
    db.refresh(estimate)
    return estimate


@router.delete("/{estimate_id}", status_code=204)
def delete_estimate(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft delete an estimate. Only the owner can delete."""
    estimate = _get_estimate_for_user(estimate_id, current_user, db, require_owner=True)
    
    estimate.is_deleted = True
    estimate.updated_by = current_user.user_id
    db.commit()


@router.post("/{estimate_id}/duplicate", response_model=EstimateResponse)
def duplicate_estimate(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Duplicate an estimate. New estimate is owned by the current user."""
    original = _get_estimate_for_user(estimate_id, current_user, db)
    
    # Create new estimate owned by current user
    new_estimate = Estimate(
        estimate_name=f"{original.estimate_name} (Copy)",
        owner_user_id=current_user.user_id,  # New owner is current user
        customer_name=original.customer_name,
        cloud=original.cloud,
        region=original.region,
        tier=original.tier,
        status="draft",
        template_id=original.template_id,
        original_prompt=original.original_prompt
    )
    db.add(new_estimate)
    db.flush()
    
    # Copy line items - only copy fields that exist in the model
    for original_item in original.line_items:
        new_item = LineItem(
            estimate_id=new_estimate.estimate_id,
            display_order=original_item.display_order,
            workload_name=original_item.workload_name,
            workload_type=original_item.workload_type,
            cloud=original_item.cloud,
            # Serverless
            serverless_enabled=original_item.serverless_enabled,
            serverless_mode=original_item.serverless_mode,
            # Classic Compute
            photon_enabled=original_item.photon_enabled,
            driver_node_type=original_item.driver_node_type,
            worker_node_type=original_item.worker_node_type,
            num_workers=original_item.num_workers,
            # DLT
            dlt_edition=original_item.dlt_edition,
            # DBSQL
            dbsql_warehouse_type=original_item.dbsql_warehouse_type,
            dbsql_warehouse_size=original_item.dbsql_warehouse_size,
            dbsql_num_clusters=original_item.dbsql_num_clusters,
            dbsql_vm_pricing_tier=original_item.dbsql_vm_pricing_tier,
            dbsql_vm_payment_option=original_item.dbsql_vm_payment_option,
            # Vector Search
            vector_search_mode=original_item.vector_search_mode,
            vector_capacity_millions=original_item.vector_capacity_millions,
            vector_search_storage_gb=original_item.vector_search_storage_gb,
            # Model Serving
            model_serving_gpu_type=original_item.model_serving_gpu_type,
            model_serving_concurrency=original_item.model_serving_concurrency,
            model_serving_scale_out=original_item.model_serving_scale_out,
            # FMAPI
            fmapi_provider=original_item.fmapi_provider,
            fmapi_model=original_item.fmapi_model,
            fmapi_endpoint_type=original_item.fmapi_endpoint_type,
            fmapi_context_length=original_item.fmapi_context_length,
            fmapi_rate_type=original_item.fmapi_rate_type,
            fmapi_quantity=original_item.fmapi_quantity,
            # Lakebase
            lakebase_cu=original_item.lakebase_cu,
            lakebase_storage_gb=original_item.lakebase_storage_gb,
            lakebase_ha_nodes=original_item.lakebase_ha_nodes,
            lakebase_backup_retention_days=original_item.lakebase_backup_retention_days,
            # Usage
            runs_per_day=original_item.runs_per_day,
            avg_runtime_minutes=original_item.avg_runtime_minutes,
            days_per_month=original_item.days_per_month,
            hours_per_month=original_item.hours_per_month,
            # Pricing
            driver_pricing_tier=original_item.driver_pricing_tier,
            worker_pricing_tier=original_item.worker_pricing_tier,
            driver_payment_option=original_item.driver_payment_option,
            worker_payment_option=original_item.worker_payment_option,
            # Additional
            workload_config=original_item.workload_config,
            notes=original_item.notes
        )
        db.add(new_item)
    
    db.commit()
    db.refresh(new_estimate)
    return new_estimate


@router.post("/{estimate_id}/clone", response_model=EstimateResponse)
def clone_estimate(
    estimate_id: UUID,
    payload: Optional[CloneRequest] = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clone an estimate with all its line items.
    
    Optionally provide a new_name in the request body.
    The cloned estimate is owned by the current user.
    """
    original = _get_estimate_for_user(estimate_id, current_user, db)
    
    # Get new name from payload or generate from original
    new_name = payload.new_name if payload and payload.new_name else f"{original.estimate_name} (Copy)"
    
    # Create new estimate owned by current user
    new_estimate = Estimate(
        estimate_name=new_name,
        owner_user_id=current_user.user_id,
        customer_name=original.customer_name,
        cloud=original.cloud,
        region=original.region,
        tier=original.tier,
        status="draft",
        template_id=original.template_id,
        original_prompt=original.original_prompt
    )
    db.add(new_estimate)
    db.flush()
    
    # Copy line items - only copy fields that exist in the model
    for original_item in original.line_items:
        new_item = LineItem(
            estimate_id=new_estimate.estimate_id,
            display_order=original_item.display_order,
            workload_name=original_item.workload_name,
            workload_type=original_item.workload_type,
            cloud=original_item.cloud,
            # Serverless
            serverless_enabled=original_item.serverless_enabled,
            serverless_mode=original_item.serverless_mode,
            # Classic Compute
            photon_enabled=original_item.photon_enabled,
            driver_node_type=original_item.driver_node_type,
            worker_node_type=original_item.worker_node_type,
            num_workers=original_item.num_workers,
            # DLT
            dlt_edition=original_item.dlt_edition,
            # DBSQL
            dbsql_warehouse_type=original_item.dbsql_warehouse_type,
            dbsql_warehouse_size=original_item.dbsql_warehouse_size,
            dbsql_num_clusters=original_item.dbsql_num_clusters,
            dbsql_vm_pricing_tier=original_item.dbsql_vm_pricing_tier,
            dbsql_vm_payment_option=original_item.dbsql_vm_payment_option,
            # Vector Search
            vector_search_mode=original_item.vector_search_mode,
            vector_capacity_millions=original_item.vector_capacity_millions,
            vector_search_storage_gb=original_item.vector_search_storage_gb,
            # Model Serving
            model_serving_gpu_type=original_item.model_serving_gpu_type,
            model_serving_concurrency=original_item.model_serving_concurrency,
            model_serving_scale_out=original_item.model_serving_scale_out,
            # FMAPI
            fmapi_provider=original_item.fmapi_provider,
            fmapi_model=original_item.fmapi_model,
            fmapi_endpoint_type=original_item.fmapi_endpoint_type,
            fmapi_context_length=original_item.fmapi_context_length,
            fmapi_rate_type=original_item.fmapi_rate_type,
            fmapi_quantity=original_item.fmapi_quantity,
            # Lakebase
            lakebase_cu=original_item.lakebase_cu,
            lakebase_storage_gb=original_item.lakebase_storage_gb,
            lakebase_ha_nodes=original_item.lakebase_ha_nodes,
            lakebase_backup_retention_days=original_item.lakebase_backup_retention_days,
            # Usage
            runs_per_day=original_item.runs_per_day,
            avg_runtime_minutes=original_item.avg_runtime_minutes,
            days_per_month=original_item.days_per_month,
            hours_per_month=original_item.hours_per_month,
            # Pricing
            driver_pricing_tier=original_item.driver_pricing_tier,
            worker_pricing_tier=original_item.worker_pricing_tier,
            driver_payment_option=original_item.driver_payment_option,
            worker_payment_option=original_item.worker_payment_option,
            # Additional
            workload_config=original_item.workload_config,
            notes=original_item.notes
        )
        db.add(new_item)
    
    db.commit()
    db.refresh(new_estimate)
    return new_estimate


