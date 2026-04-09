"""Calculate endpoints package — aggregates all workload calculation sub-routers."""
from fastapi import APIRouter

from app.routes.calculate.jobs import router as jobs_router
from app.routes.calculate.all_purpose import router as all_purpose_router
from app.routes.calculate.dbsql_calc import router as dbsql_router
from app.routes.calculate.dlt_calc import router as dlt_router
from app.routes.calculate.model_serving_calc import router as model_serving_router
from app.routes.calculate.fmapi_calc import router as fmapi_router
from app.routes.calculate.vector_search_calc import router as vector_search_router
from app.routes.calculate.lakebase_calc import router as lakebase_router
from app.routes.calculate.databricks_apps_calc import router as databricks_apps_router
from app.routes.calculate.clean_room_calc import router as clean_room_router
from app.routes.calculate.ai_parse_calc import router as ai_parse_router
from app.routes.calculate.shutterstock_calc import router as shutterstock_router
from app.routes.calculate.lakeflow_connect_calc import router as lakeflow_connect_router

router = APIRouter(tags=["Cost Calculation"])
router.include_router(jobs_router)
router.include_router(all_purpose_router)
router.include_router(dbsql_router)
router.include_router(dlt_router)
router.include_router(model_serving_router)
router.include_router(fmapi_router)
router.include_router(vector_search_router)
router.include_router(lakebase_router)
router.include_router(databricks_apps_router)
router.include_router(clean_room_router)
router.include_router(ai_parse_router)
router.include_router(shutterstock_router)
router.include_router(lakeflow_connect_router)
