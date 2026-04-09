"""Reference data endpoints — direct Lakebase queries with caching."""
from fastapi import APIRouter

from app.routes.reference.clouds_regions import router as clouds_regions_router
from app.routes.reference.instances import router as instances_router
from app.routes.reference.dbsql import router as dbsql_router
from app.routes.reference.dlt import router as dlt_router
from app.routes.reference.vector_search import router as vector_search_router
from app.routes.reference.lakebase_ref import router as lakebase_ref_router
from app.routes.reference.photon import router as photon_router
from app.routes.reference.serverless import router as serverless_router
from app.routes.reference.pricing import router as pricing_router
from app.routes.reference.model_serving import router as model_serving_router
from app.routes.reference.fmapi import router as fmapi_router

router = APIRouter(tags=["Reference Data"])

router.include_router(clouds_regions_router)
router.include_router(instances_router)
router.include_router(dbsql_router)
router.include_router(dlt_router)
router.include_router(vector_search_router)
router.include_router(lakebase_ref_router)
router.include_router(photon_router)
router.include_router(serverless_router)
router.include_router(pricing_router)
router.include_router(model_serving_router)
router.include_router(fmapi_router)
