"""VM Pricing API routes - fetches data from Lakebase sync_pricing_vm_costs table."""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct, func

from app.database import get_db
from app.models.vm_pricing import VMPricing
from app.schemas.vm_pricing import (
    VMPricingResponse,
    VMPricingTierResponse,
    VMPaymentOptionResponse
)
from app.config import log_warning

router = APIRouter(prefix="/vm-pricing", tags=["vm-pricing"])


# Default VM pricing for fallback
DEFAULT_VM_PRICING = {
    "aws": {
        "i3.xlarge": {"on_demand": 0.312, "spot": 0.094},
        "i3.2xlarge": {"on_demand": 0.624, "spot": 0.187},
        "i3.4xlarge": {"on_demand": 1.248, "spot": 0.374},
        "i3.8xlarge": {"on_demand": 2.496, "spot": 0.749},
        "i3.16xlarge": {"on_demand": 4.992, "spot": 1.498},
        "m5.large": {"on_demand": 0.096, "spot": 0.029},
        "m5.xlarge": {"on_demand": 0.192, "spot": 0.058},
        "m5.2xlarge": {"on_demand": 0.384, "spot": 0.115},
        "m5.4xlarge": {"on_demand": 0.768, "spot": 0.230},
        "m5d.xlarge": {"on_demand": 0.226, "spot": 0.068},
        "m5d.2xlarge": {"on_demand": 0.452, "spot": 0.136},
        "m5d.4xlarge": {"on_demand": 0.904, "spot": 0.271},
        "m5d.12xlarge": {"on_demand": 2.712, "spot": 0.814},
        "m5d.16xlarge": {"on_demand": 3.616, "spot": 1.085},
        "r5.large": {"on_demand": 0.126, "spot": 0.038},
        "r5.xlarge": {"on_demand": 0.252, "spot": 0.076},
        "r5.2xlarge": {"on_demand": 0.504, "spot": 0.151},
        "r5d.xlarge": {"on_demand": 0.288, "spot": 0.086},
        "r5d.2xlarge": {"on_demand": 0.576, "spot": 0.173},
        "c5.xlarge": {"on_demand": 0.170, "spot": 0.051},
        "c5.2xlarge": {"on_demand": 0.340, "spot": 0.102},
        "p3.2xlarge": {"on_demand": 3.060, "spot": 0.918},
        "p3.8xlarge": {"on_demand": 12.240, "spot": 3.672},
    },
    "azure": {
        "Standard_DS3_v2": {"on_demand": 0.293},
        "Standard_DS4_v2": {"on_demand": 0.585},
        "Standard_DS5_v2": {"on_demand": 1.170},
        "Standard_D4s_v3": {"on_demand": 0.192},
        "Standard_D8s_v3": {"on_demand": 0.384},
        "Standard_D16s_v3": {"on_demand": 0.768},
        "Standard_E4s_v3": {"on_demand": 0.252},
        "Standard_E8s_v3": {"on_demand": 0.504},
        "Standard_L8s_v2": {"on_demand": 0.624},
        "Standard_NC6s_v3": {"on_demand": 3.060},
    },
    "gcp": {
        "n1-standard-4": {"on_demand": 0.150},
        "n1-standard-8": {"on_demand": 0.301},
        "n1-standard-16": {"on_demand": 0.602},
        "n1-standard-32": {"on_demand": 1.204},
        "n1-highmem-4": {"on_demand": 0.187},
        "n1-highmem-8": {"on_demand": 0.374},
        "n2-standard-4": {"on_demand": 0.194},
        "n2-standard-8": {"on_demand": 0.388},
    }
}


@router.get("", response_model=List[VMPricingResponse])
@router.get("/", response_model=List[VMPricingResponse])
def list_vm_pricing(
    cloud: str = Query(..., description="Cloud provider (aws, azure, gcp)"),
    region: Optional[str] = Query(None, description="Cloud region (region_code format, e.g., ap-southeast-1)"),
    instance_type: Optional[str] = Query(None, description="Instance type"),
    pricing_tier: Optional[str] = Query(None, description="Pricing tier (on_demand, spot, reserved_1y, reserved_3y)"),
    db: Session = Depends(get_db)
):
    """Get VM pricing data from Lakebase, with hardcoded fallback."""
    try:
        query = db.query(VMPricing).filter(VMPricing.cloud == cloud.upper())
        
        if region:
            query = query.filter(VMPricing.region == region)
        if instance_type:
            query = query.filter(VMPricing.instance_type == instance_type)
        if pricing_tier:
            query = query.filter(VMPricing.pricing_tier == pricing_tier)
        
        results = query.order_by(VMPricing.instance_type, VMPricing.pricing_tier).all()
        
        if results:
            return results
    except Exception as e:
        log_warning(f"Could not fetch VM pricing from database: {e}")
    
    # Return default pricing as fallback
    return _get_default_pricing(cloud, region, instance_type, pricing_tier)


@router.get("/instance-types")
def get_instance_types_for_region(
    cloud: str = Query(..., description="Cloud provider"),
    region: Optional[str] = Query(None, description="Cloud region"),
    db: Session = Depends(get_db)
):
    """Get unique instance types available for a cloud/region from Lakebase."""
    try:
        query = db.query(distinct(VMPricing.instance_type)).filter(
            VMPricing.cloud == cloud.upper()
        )
        
        if region:
            query = query.filter(VMPricing.region == region)
        
        results = query.order_by(VMPricing.instance_type).all()
        
        if results:
            return [{"instance_type": r[0]} for r in results]
    except Exception as e:
        log_warning(f"Could not fetch instance types from database: {e}")
    
    # Return default instance types for the cloud
    cloud_lower = cloud.lower()
    if cloud_lower in DEFAULT_VM_PRICING:
        return [{"instance_type": it} for it in sorted(DEFAULT_VM_PRICING[cloud_lower].keys())]
    return []


@router.get("/regions")
def get_regions_for_cloud(
    cloud: str = Query(..., description="Cloud provider"),
    db: Session = Depends(get_db)
):
    """Get unique regions available for a cloud from Lakebase."""
    try:
        results = db.query(distinct(VMPricing.region)).filter(
            VMPricing.cloud == cloud.upper()
        ).order_by(VMPricing.region).all()
        
        if results:
            return [{"region": r[0]} for r in results]
    except Exception as e:
        log_warning(f"Could not fetch regions from database: {e}")
    
    return []


@router.get("/price")
def get_vm_price(
    cloud: str = Query(..., description="Cloud provider"),
    region: str = Query(..., description="Cloud region"),
    instance_type: str = Query(..., description="Instance type"),
    pricing_tier: str = Query("on_demand", description="Pricing tier"),
    payment_option: Optional[str] = Query(None, description="Payment option for reserved (AWS only)"),
    db: Session = Depends(get_db)
):
    """Get specific VM price for a given configuration."""
    try:
        query = db.query(VMPricing).filter(
            VMPricing.cloud == cloud.upper(),
            VMPricing.region == region,
            VMPricing.instance_type == instance_type,
            VMPricing.pricing_tier == pricing_tier
        )
        
        if payment_option and pricing_tier.startswith("reserved"):
            query = query.filter(VMPricing.payment_option == payment_option)
        
        result = query.first()
        
        if result:
            return {
                "cost_per_hour": result.cost_per_hour,
                "currency": result.currency,
                "pricing_tier": result.pricing_tier,
                "payment_option": result.payment_option,
                "source": result.source
            }
    except Exception as e:
        log_warning(f"Could not fetch VM price from database: {e}")
    
    # Fallback to default pricing
    cloud_lower = cloud.lower()
    if cloud_lower in DEFAULT_VM_PRICING:
        if instance_type in DEFAULT_VM_PRICING[cloud_lower]:
            tier_key = "on_demand" if pricing_tier == "on_demand" else pricing_tier
            if tier_key in DEFAULT_VM_PRICING[cloud_lower][instance_type]:
                return {
                    "cost_per_hour": DEFAULT_VM_PRICING[cloud_lower][instance_type][tier_key],
                    "currency": "USD",
                    "pricing_tier": pricing_tier,
                    "payment_option": payment_option or "NA",
                    "source": "fallback"
                }
    
    return {
        "cost_per_hour": 0.20,
        "currency": "USD",
        "pricing_tier": pricing_tier,
        "payment_option": payment_option or "NA",
        "source": "default"
    }


@router.get("/tiers", response_model=List[VMPricingTierResponse])
def get_pricing_tiers():
    """Get available VM pricing tiers."""
    return [
        {"id": "on_demand", "name": "On-Demand", "description": "Pay as you go with no commitment"},
        {"id": "spot", "name": "Spot Instances", "description": "Up to 90% discount, can be interrupted"},
        {"id": "reserved_1y", "name": "1-Year Reserved", "description": "1-year commitment for lower rates"},
        {"id": "reserved_3y", "name": "3-Year Reserved", "description": "3-year commitment for lowest rates"},
    ]


@router.get("/payment-options", response_model=List[VMPaymentOptionResponse])
def get_payment_options():
    """Get available payment options for reserved instances (AWS only)."""
    return [
        {"id": "no_upfront", "name": "No Upfront", "description": "Pay monthly with no upfront payment"},
        {"id": "partial_upfront", "name": "Partial Upfront", "description": "Pay partial upfront, lower monthly"},
        {"id": "all_upfront", "name": "All Upfront", "description": "Pay all upfront for lowest total cost"},
    ]


def _get_default_pricing(cloud: str, region: Optional[str], instance_type: Optional[str], pricing_tier: Optional[str]) -> List[dict]:
    """Generate default pricing responses when database is not available."""
    cloud_lower = cloud.lower()
    
    if cloud_lower not in DEFAULT_VM_PRICING:
        return []
    
    results = []
    for it, tiers in DEFAULT_VM_PRICING[cloud_lower].items():
        if instance_type and it != instance_type:
            continue
        
        for tier, price in tiers.items():
            if pricing_tier and tier != pricing_tier:
                continue
            
            results.append({
                "cloud": cloud.upper(),
                "region": region or "default",
                "instance_type": it,
                "pricing_tier": tier,
                "payment_option": "NA",
                "cost_per_hour": price,
                "currency": "USD",
                "source": "fallback",
                "fetched_at": None,
                "updated_at": None
            })
    
    return results

