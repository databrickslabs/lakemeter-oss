"""Pydantic request/response models for calculation endpoints."""
from typing import Optional
from pydantic import BaseModel, Field


class GlobalDiscountConfig(BaseModel):
    """Global discount configuration by category.

    Cross-service (EA) discount rules per
    https://www.databricks.com/product/sku-groups#exclusions:
    INCLUDED: Jobs, All-Purpose, DLT, SQL, Serverless SQL, Database Serverless, etc.
    EXCLUDED: Model Serving inference, Model Training, FMAPI proprietary, Data Transfer, Storage.
    """

    dbu_discount: float = Field(default=0, ge=0, le=100, description="Cross-service DBU discount % (0-100)")
    vm_discount: float = Field(default=0, ge=0, le=100, description="VM discount percentage (0-100)")
    storage_discount: float = Field(default=0, ge=0, le=100, description="Storage discount percentage (0-100)")
    platform_addon_discount: float = Field(default=0, ge=0, le=100, description="Platform add-on discount percentage (0-100)")
    support_discount: float = Field(default=0, ge=0, le=100, description="Support discount percentage (0-100)")


class DiscountConfig(BaseModel):
    """Discount configuration for cost calculations.

    Resolution order per SKU:
    1. sku_specific exact match (highest priority, ignores eligibility)
    2. global.dbu_discount (only if cross-service eligible)
    3. global.vm_discount / storage_discount / etc. by category
    4. No match -> 0%
    """

    global_discounts: GlobalDiscountConfig = Field(alias="global", description="Global discounts by category")
    sku_specific: dict[str, float] = Field(default={}, description="SKU-specific discount overrides (SKU -> %)")
    notes: Optional[str] = Field(default=None, description="Notes about the discount")
    effective_date: Optional[str] = Field(default=None, description="When discount becomes effective (YYYY-MM-DD)")
    expiry_date: Optional[str] = Field(default=None, description="When discount expires (YYYY-MM-DD)")

    model_config = {"populate_by_name": True}

    def validate_sku_specific(self) -> list[str]:
        errors = []
        for sku, discount_pct in self.sku_specific.items():
            if not isinstance(discount_pct, (int, float)):
                errors.append(f"SKU '{sku}': discount must be a number, got {type(discount_pct).__name__}")
            elif discount_pct < 0 or discount_pct > 100:
                errors.append(f"SKU '{sku}': discount must be between 0 and 100, got {discount_pct}")
        return errors


# ── Workload Calculation Request Models ─────────────────────────────────────


class JobsClassicCalculationRequest(BaseModel):
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code (e.g., us-east-1)")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    driver_node_type: str = Field(..., description="Driver instance type")
    worker_node_type: str = Field(..., description="Worker instance type")
    num_workers: int = Field(..., ge=0, description="Number of worker nodes")
    photon_enabled: bool = Field(default=False, description="Enable Photon acceleration")
    driver_pricing_tier: str = Field(default="on_demand", description="Driver VM pricing tier")
    worker_pricing_tier: str = Field(default="on_demand", description="Worker VM pricing tier")
    driver_payment_option: Optional[str] = Field(default="NA", description="Payment option for reserved instances")
    worker_payment_option: Optional[str] = Field(default="NA", description="Payment option for reserved instances")
    runs_per_day: Optional[int] = Field(None, ge=0, description="Number of job runs per day")
    avg_runtime_minutes: Optional[int] = Field(None, ge=0, description="Average runtime per run in minutes")
    days_per_month: Optional[int] = Field(None, ge=1, le=31, description="Number of days per month")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct hours per month")
    discount_config: Optional[DiscountConfig] = Field(None, description="Discount configuration")


class JobsServerlessCalculationRequest(BaseModel):
    cloud: str = Field(..., description="Cloud provider: AWS, AZURE, GCP")
    region: str = Field(..., description="Region code")
    tier: str = Field(..., description="Pricing tier: STANDARD, PREMIUM, ENTERPRISE")
    driver_node_type: Optional[str] = Field(None, description="Driver instance type (for DBU estimation)")
    worker_node_type: Optional[str] = Field(None, description="Worker instance type (for DBU estimation)")
    num_workers: Optional[int] = Field(None, ge=0, description="Number of workers (for DBU estimation)")
    runs_per_day: Optional[int] = Field(None, ge=0)
    avg_runtime_minutes: Optional[int] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    serverless_mode: str = Field(default="standard", description="standard or performance")
    discount_config: Optional[DiscountConfig] = Field(None)


class AllPurposeClassicCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    driver_node_type: str = Field(...)
    worker_node_type: str = Field(...)
    num_workers: int = Field(..., ge=0)
    photon_enabled: bool = Field(default=False)
    driver_pricing_tier: str = Field(default="on_demand")
    worker_pricing_tier: str = Field(default="on_demand")
    driver_payment_option: Optional[str] = Field(default="NA")
    worker_payment_option: Optional[str] = Field(default="NA")
    hours_per_day: Optional[float] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class AllPurposeServerlessCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    driver_node_type: Optional[str] = Field(None, description="Driver instance type (for DBU estimation)")
    worker_node_type: Optional[str] = Field(None, description="Worker instance type (for DBU estimation)")
    num_workers: Optional[int] = Field(None, ge=0, description="Number of workers (for DBU estimation)")
    hours_per_day: Optional[float] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    serverless_mode: str = Field(default="standard")
    discount_config: Optional[DiscountConfig] = Field(None)


class DBSQLClassicProCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    warehouse_type: str = Field(..., description="CLASSIC or PRO")
    warehouse_size: str = Field(..., description="e.g., Medium, X-Small")
    driver_pricing_tier: str = Field(default="on_demand")
    worker_pricing_tier: str = Field(default="on_demand")
    driver_payment_option: Optional[str] = Field(default="NA")
    worker_payment_option: Optional[str] = Field(default="NA")
    hours_per_day: Optional[float] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class DBSQLServerlessCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    warehouse_size: str = Field(...)
    hours_per_day: Optional[float] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class DLTClassicCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    dlt_edition: str = Field(default="CORE", description="CORE, PRO, ADVANCED")
    driver_node_type: str = Field(...)
    worker_node_type: str = Field(...)
    num_workers: int = Field(..., ge=0)
    photon_enabled: bool = Field(default=False)
    driver_pricing_tier: str = Field(default="on_demand")
    worker_pricing_tier: str = Field(default="on_demand")
    driver_payment_option: Optional[str] = Field(default="NA")
    worker_payment_option: Optional[str] = Field(default="NA")
    runs_per_day: Optional[int] = Field(None, ge=0)
    avg_runtime_minutes: Optional[int] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class DLTServerlessCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    dlt_edition: str = Field(default="CORE")
    driver_node_type: Optional[str] = Field(None, description="Driver instance type (for DBU estimation)")
    worker_node_type: Optional[str] = Field(None, description="Worker instance type (for DBU estimation)")
    num_workers: Optional[int] = Field(None, ge=0, description="Number of workers (for DBU estimation)")
    runs_per_day: Optional[int] = Field(None, ge=0)
    avg_runtime_minutes: Optional[int] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    serverless_mode: str = Field(default="standard")
    discount_config: Optional[DiscountConfig] = Field(None)


class ModelServingCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    gpu_type: str = Field(...)
    scale_out: str = Field(default="small", description="small, medium, large, or custom")
    custom_concurrency: Optional[int] = Field(None, ge=4, description="Custom concurrency (multiple of 4)")
    hours_per_day: Optional[float] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class FMAPIDatabricksCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    model: str = Field(...)
    # Frontend sends quantity + rate_type (single rate per request)
    quantity: Optional[float] = Field(None, ge=0, description="Token quantity (in millions) or hours")
    rate_type: Optional[str] = Field(None, description="input_token, output_token, cache_read, cache_write, batch_inference")
    # Legacy fields (still supported for backward compat)
    input_tokens_per_month: Optional[float] = Field(None, ge=0)
    output_tokens_per_month: Optional[float] = Field(None, ge=0)
    provisioned_hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class FMAPIProprietaryCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    provider: str = Field(...)
    model: str = Field(...)
    endpoint_type: str = Field(default="in_geo")
    context_length: Optional[str] = Field(None)
    # Frontend sends quantity + rate_type (single rate per request)
    quantity: Optional[float] = Field(None, ge=0, description="Token quantity (in millions) or hours")
    rate_type: Optional[str] = Field(None, description="input_token, output_token, cache_read, cache_write, batch_inference")
    # Legacy fields (still supported for backward compat)
    input_tokens_per_month: Optional[float] = Field(None, ge=0)
    output_tokens_per_month: Optional[float] = Field(None, ge=0)
    provisioned_hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class VectorSearchCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    mode: str = Field(..., description="standard or storage_optimized")
    num_vectors_millions: float = Field(..., ge=0, description="Number of vectors in millions")
    hours_per_day: Optional[float] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class DatabricksAppsCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    size: str = Field(default="medium", description="medium or large")
    hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class CleanRoomCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    collaborators: int = Field(..., ge=1, le=10, description="Number of collaborators (1-10)")
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    discount_config: Optional[DiscountConfig] = Field(None)


class AIParseCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    mode: str = Field(default="pages", description="dbu (direct) or pages (pages-based)")
    complexity: Optional[str] = Field(None, description="low_text, low_images, medium, high")
    pages_thousands: Optional[float] = Field(None, ge=0, description="Number of pages (in thousands)")
    hours_per_month: Optional[float] = Field(None, ge=0, description="Direct DBU hours (for dbu mode)")
    discount_config: Optional[DiscountConfig] = Field(None)


class ShutterstockImageAICalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    images_per_month: int = Field(..., ge=0, description="Number of images per month")
    discount_config: Optional[DiscountConfig] = Field(None)


class LakeflowConnectCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    # Pipeline (DLT Serverless)
    dlt_edition: str = Field(default="ADVANCED", description="DLT edition: CORE, PRO, ADVANCED")
    runs_per_day: Optional[int] = Field(None, ge=0)
    avg_runtime_minutes: Optional[int] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    # Gateway (classic DLT Advanced, database connectors only)
    gateway_enabled: bool = Field(default=False)
    gateway_instance_type: Optional[str] = Field(None, description="Gateway instance type")
    gateway_pricing_tier: str = Field(default="on_demand")
    gateway_payment_option: Optional[str] = Field(default="NA")
    gateway_hours_per_month: Optional[float] = Field(None, ge=0)
    discount_config: Optional[DiscountConfig] = Field(None)


class LakebaseCalculationRequest(BaseModel):
    cloud: str = Field(...)
    region: str = Field(...)
    tier: str = Field(...)
    cu_size: float = Field(...)
    read_replicas: int = Field(default=0, ge=0)
    num_nodes: Optional[int] = Field(None, ge=1, le=3, description="Total nodes (frontend sends this; alternative to read_replicas)")
    hours_per_day: Optional[float] = Field(None, ge=0)
    days_per_month: Optional[int] = Field(None, ge=1, le=31)
    hours_per_month: Optional[float] = Field(None, ge=0)
    storage_gb: Optional[float] = Field(None, ge=0, le=8192, description="Database storage in GB")
    pitr_gb: Optional[float] = Field(None, ge=0, description="Point-in-time restore storage in GB")
    snapshot_gb: Optional[float] = Field(None, ge=0, description="Snapshot storage in GB")
    discount_config: Optional[DiscountConfig] = Field(None)
