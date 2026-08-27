"""FMAPI (Foundation Model API) reference endpoints — Databricks and Proprietary models."""
import logging
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import ref_cache
from app.services.fmapi_pricing import (
    FMAPI_DATABRICKS_RATES,
    FMAPI_PROPRIETARY_RATES,
    FMAPIRateNotFound,
    active_databricks_models,
    active_proprietary_models,
    get_proprietary_rate,
)
from app.services.validators import (
    validate_cloud,
    validate_fmapi_databricks_model,
    validate_fmapi_databricks_rate_type,
    validate_fmapi_proprietary_provider,
    validate_fmapi_proprietary_model,
    validate_fmapi_proprietary_endpoint_type,
    validate_fmapi_proprietary_context_length,
    validate_fmapi_proprietary_rate_type,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Databricks FMAPI ────────────────────────────────────────────────────────


@router.get("/fmapi/databricks-models/list", tags=["FMAPI - Databricks"])
def list_fmapi_databricks_models(db: Session = Depends(get_db)):
    cached = ref_cache.get("fmapi_db_models_list")
    if cached is not None:
        return cached

    models = [model["id"] for model in active_databricks_models()]
    response = {"success": True, "data": {"count": len(models), "models": models}}
    ref_cache.set("fmapi_db_models_list", response)
    return response


@router.get("/fmapi/databricks-models", tags=["FMAPI - Databricks"])
def get_fmapi_databricks_models(
    model: str = Query(..., description="Model name (required)"),
    cloud: str = Query(None, description="Filter by cloud: AWS, AZURE, GCP"),
    rate_type: str = Query(None, description="Filter by rate type"),
    db: Session = Depends(get_db),
):
    error = validate_fmapi_databricks_model(model, db)
    if error:
        return error

    if cloud:
        error = validate_cloud(cloud)
        if error:
            return error

    if rate_type:
        error = validate_fmapi_databricks_rate_type(model, rate_type, db)
        if error:
            return error

    try:
        where_conditions = ["model = :model"]
        params = {"model": model}

        if cloud:
            where_conditions.append("cloud = :cloud")
            params["cloud"] = cloud.upper()
        if rate_type:
            where_conditions.append("rate_type = :rate_type")
            params["rate_type"] = rate_type

        where_clause = "WHERE " + " AND ".join(where_conditions)

        query = text(f"""
            SELECT cloud, model, rate_type, dbu_rate, input_divisor, is_hourly
            FROM lakemeter.sync_product_fmapi_databricks
            {where_clause}
            ORDER BY cloud, model, rate_type
        """)
        results = db.execute(query, params).fetchall()

        models_dict = {}
        for r in results:
            key = f"{r.cloud}:{r.model}"
            if key not in models_dict:
                models_dict[key] = {"cloud": r.cloud, "model": r.model, "pricing": []}

            pricing_entry = {"rate_type": r.rate_type}
            if r.is_hourly:
                pricing_entry["dbu_per_hour"] = float(r.dbu_rate) if r.dbu_rate else None
            elif r.input_divisor == 1000000:
                pricing_entry["dbu_per_1M_tokens"] = float(r.dbu_rate) if r.dbu_rate else None
            else:
                pricing_entry["dbu_rate"] = float(r.dbu_rate) if r.dbu_rate else None
                pricing_entry["input_divisor"] = float(r.input_divisor) if r.input_divisor else None

            models_dict[key]["pricing"].append(pricing_entry)

        return {
            "success": True,
            "data": {
                "model_filter": model,
                "cloud_filter": cloud.upper() if cloud else None,
                "rate_type_filter": rate_type if rate_type else None,
                "count": len(models_dict),
                "models": list(models_dict.values()),
            },
        }
    except Exception as e:
        logger.error(f"Error fetching FMAPI Databricks models: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


# ── Proprietary FMAPI ───────────────────────────────────────────────────────


@router.get("/fmapi/proprietary-models/list", tags=["FMAPI - Proprietary"])
def list_fmapi_proprietary_models(
    provider: str = Query(..., description="Provider (required): openai, anthropic, google"),
    db: Session = Depends(get_db),
):
    error = validate_fmapi_proprietary_provider(provider, db)
    if error:
        return error

    cached = ref_cache.get("fmapi_prop_models_list", provider=provider)
    if cached is not None:
        return cached

    provider_models = active_proprietary_models().get(provider.lower(), [])
    models = [model["id"] for model in provider_models]
    response = {
        "success": True,
        "data": {"provider": provider, "count": len(models), "models": models},
    }
    ref_cache.set("fmapi_prop_models_list", response, provider=provider)
    return response


@router.get("/fmapi/proprietary-models/options", tags=["FMAPI - Proprietary"])
def get_fmapi_proprietary_model_options(
    provider: str = Query(..., description="Provider (required): openai, anthropic, google"),
    model: str = Query(..., description="Model name (required)"),
    db: Session = Depends(get_db),
):
    error = validate_fmapi_proprietary_provider(provider, db)
    if error:
        return error
    error = validate_fmapi_proprietary_model(model, provider, db)
    if error:
        return error

    try:
        query = text("""
            SELECT DISTINCT context_length, rate_type, endpoint_type
            FROM lakemeter.sync_product_fmapi_proprietary
            WHERE provider = :provider AND model = :model
            ORDER BY endpoint_type, context_length, rate_type
        """)
        results = db.execute(query, {"provider": provider.lower(), "model": model}).fetchall()

        context_lengths = sorted(list(set([r.context_length for r in results])))
        rate_types = sorted(list(set([r.rate_type for r in results])))
        endpoint_types = sorted(list(set([r.endpoint_type for r in results])))

        return {
            "success": True,
            "data": {
                "provider": provider,
                "model": model,
                "available_context_lengths": context_lengths,
                "available_rate_types": rate_types,
                "available_endpoint_types": endpoint_types,
            },
        }
    except Exception as e:
        logger.error(f"Error fetching proprietary FMAPI model options: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


@router.get("/fmapi/proprietary-models", tags=["FMAPI - Proprietary"])
def get_fmapi_proprietary_models(
    provider: str = Query(..., description="Provider (required): openai, anthropic, google"),
    cloud: str = Query(None, description="Filter by cloud: AWS, AZURE, GCP"),
    model: str = Query(None, description="Filter by model name"),
    endpoint_type: str = Query(None, description="Filter by endpoint type"),
    context_length: str = Query(None, description="Filter by context length"),
    rate_type: str = Query(None, description="Filter by rate type"),
    db: Session = Depends(get_db),
):
    error = validate_fmapi_proprietary_provider(provider, db)
    if error:
        return error

    if cloud:
        error = validate_cloud(cloud)
        if error:
            return error

    if model:
        error = validate_fmapi_proprietary_model(model, provider, db)
        if error:
            return error

    if endpoint_type:
        if not model:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "endpoint_type filter requires model parameter to be specified",
                    "field": "endpoint_type",
                },
            }
        error = validate_fmapi_proprietary_endpoint_type(provider, model, endpoint_type, db)
        if error:
            return error

    if context_length:
        if not model:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "context_length filter requires model parameter to be specified",
                    "field": "context_length",
                },
            }
        error = validate_fmapi_proprietary_context_length(provider, model, context_length, endpoint_type, db)
        if error:
            return error

    if rate_type:
        if not model:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_PARAMETER",
                    "message": "rate_type filter requires model parameter to be specified",
                    "field": "rate_type",
                },
            }
        error = validate_fmapi_proprietary_rate_type(provider, model, rate_type, endpoint_type, context_length, db)
        if error:
            return error

    try:
        where_conditions = ["provider = :provider"]
        params = {"provider": provider.lower()}

        if cloud:
            where_conditions.append("cloud = :cloud")
            params["cloud"] = cloud.upper()
        if model:
            where_conditions.append("model = :model")
            params["model"] = model
        if endpoint_type:
            where_conditions.append("endpoint_type = :endpoint_type")
            params["endpoint_type"] = endpoint_type
        if context_length:
            where_conditions.append("context_length = :context_length")
            params["context_length"] = context_length
        if rate_type:
            where_conditions.append("rate_type = :rate_type")
            params["rate_type"] = rate_type

        where_clause = "WHERE " + " AND ".join(where_conditions)

        query = text(f"""
            SELECT cloud, provider, model, endpoint_type, context_length,
                   rate_type, dbu_rate, input_divisor, is_hourly
            FROM lakemeter.sync_product_fmapi_proprietary
            {where_clause}
            ORDER BY cloud, provider, model, endpoint_type, context_length, rate_type
        """)
        results = db.execute(query, params).fetchall()

        models_dict = {}
        for r in results:
            try:
                current_rate = get_proprietary_rate(
                    cloud=r.cloud.lower(),
                    provider=r.provider,
                    model=r.model,
                    endpoint_type=r.endpoint_type,
                    context_length=r.context_length,
                    rate_type=r.rate_type,
                )
            except FMAPIRateNotFound:
                # Do not expose retired database rows as current catalog options.
                continue

            key = f"{r.cloud}:{r.provider}:{r.model}"
            if key not in models_dict:
                models_dict[key] = {"cloud": r.cloud, "provider": r.provider, "model": r.model, "pricing": []}

            pricing_entry = {
                "endpoint_type": r.endpoint_type,
                "context_length": r.context_length,
                "rate_type": r.rate_type,
            }
            effective_rate = current_rate["effective_dbu_rate"]
            if current_rate.get("is_hourly"):
                pricing_entry["dbu_per_hour"] = effective_rate
            elif current_rate.get("input_divisor") == 1000000:
                pricing_entry["dbu_per_1M_tokens"] = effective_rate
            else:
                pricing_entry["dbu_rate"] = effective_rate
                pricing_entry["input_divisor"] = current_rate.get("input_divisor")
            if current_rate.get("promotion_applied"):
                pricing_entry["list_dbu_rate"] = current_rate["dbu_rate"]
                pricing_entry["promotion_label"] = current_rate.get("promotion_label")
                pricing_entry["promotion_end_date"] = current_rate.get("promotion_end_date")

            models_dict[key]["pricing"].append(pricing_entry)

        return {
            "success": True,
            "data": {
                "cloud_filter": cloud.upper() if cloud else None,
                "provider_filter": provider,
                "model_filter": model if model else None,
                "endpoint_type_filter": endpoint_type if endpoint_type else None,
                "context_length_filter": context_length if context_length else None,
                "rate_type_filter": rate_type if rate_type else None,
                "count": len(models_dict),
                "models": list(models_dict.values()),
            },
        }
    except Exception as e:
        logger.error(f"Error fetching FMAPI proprietary models: {e}")
        return {"success": False, "error": {"message": str(e), "code": "DATABASE_ERROR"}}


# ── Config endpoints (for WorkloadForm dropdowns) ─────────────────────────


@router.get("/fmapi-databricks", tags=["FMAPI - Databricks"])
def get_fmapi_databricks_config(db: Session = Depends(get_db)):
    """Return FMAPI Databricks config for WorkloadForm: model types, inference types, models."""
    cached = ref_cache.get("fmapi_databricks_config")
    if cached is not None:
        return cached

    models = active_databricks_models()
    embedding = [
        model
        for model in models
        if any(key in model["id"].lower() for key in ("embed", "bge", "gte"))
    ]
    llm = [model for model in models if model not in embedding]
    rate_types = sorted(
        {
            key.split(":")[2]
            for key, rate in FMAPI_DATABRICKS_RATES.items()
            if rate.get("status", "active") == "active"
        }
    )
    response = {
        "model_types": [
            {"id": "llm", "name": "LLMs", "has_output_tokens": True},
            {
                "id": "embedding",
                "name": "Embedding Models",
                "has_output_tokens": False,
            },
        ],
        "models": {"llm": llm, "embedding": embedding},
        "inference_types": [
            {"id": rate_type, "name": rate_type.replace("_", " ").title()}
            for rate_type in rate_types
        ],
    }
    ref_cache.set("fmapi_databricks_config", response)
    return response


@router.get("/fmapi-proprietary", tags=["FMAPI - Proprietary"])
def get_fmapi_proprietary_config(db: Session = Depends(get_db)):
    """Return FMAPI Proprietary config for WorkloadForm: providers with models, endpoint types, context lengths."""
    cached = ref_cache.get("fmapi_proprietary_config")
    if cached is not None:
        return cached

    provider_models = active_proprietary_models()
    endpoint_types = sorted(
        {
            key.split(":")[3]
            for key, rate in FMAPI_PROPRIETARY_RATES.items()
            if rate.get("status", "active") == "active"
        }
    )
    context_lengths = sorted(
        {
            key.split(":")[4]
            for key, rate in FMAPI_PROPRIETARY_RATES.items()
            if rate.get("status", "active") == "active"
        }
    )
    provider_names = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "google": "Google",
    }
    response = {
        "providers": [
            {
                "id": provider,
                "name": provider_names.get(provider, provider.title()),
                "models": models,
            }
            for provider, models in provider_models.items()
        ],
        "endpoint_types": [
            {"id": endpoint, "name": endpoint.replace("_", " ").title()}
            for endpoint in endpoint_types
        ],
        "context_lengths": [
            {"id": context, "name": context.replace("_", " ").title()}
            for context in context_lengths
        ],
    }
    ref_cache.set("fmapi_proprietary_config", response)
    return response
