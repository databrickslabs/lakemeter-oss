"""FastAPI main application entry point."""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings, setup_logging, log_info
from app.routes import (
    estimates_router,
    line_items_router,
    workload_types_router,
    users_router,
    export_router,
    vm_pricing_router,
    calculate_router,
    reference_router
)
from app.routes.chat import router as chat_router

# Initialize logging based on environment
setup_logging()

# Create FastAPI application
# redirect_slashes=False prevents automatic redirects that break CORS
# Disable docs in production for cleaner deployment
app = FastAPI(
    title="Lakemeter API",
    description="Databricks Pricing Calculator API - Estimate and manage Databricks workload costs",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False
)

# Log startup info
log_info(f"Starting Lakemeter API (environment: {settings.environment})")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(estimates_router, prefix="/api/v1")
app.include_router(line_items_router, prefix="/api/v1")
app.include_router(workload_types_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(vm_pricing_router, prefix="/api/v1")
app.include_router(calculate_router, prefix="/api/v1")
app.include_router(reference_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/api")
def api_root():
    """API root endpoint."""
    return {
        "name": "Lakemeter API",
        "version": "1.0.0",
        "description": "Databricks Pricing Calculator API"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/v1/debug/headers")
def debug_headers(request: Request):
    """Debug endpoint to see what headers Databricks Apps sends."""
    from app.auth.databricks_auth import debug_headers as get_debug_headers
    return get_debug_headers(request)




@app.get("/api/v1/debug/database")
def debug_database():
    """Debug endpoint to check database connection status."""
    import os
    import uuid
    from app.auth.token_manager import token_manager
    
    result = {
        "environment_vars": {
            "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST", "NOT SET"),
            "DATABRICKS_SECRETS_SCOPE": os.getenv("DATABRICKS_SECRETS_SCOPE", "NOT SET"),
            "LAKEBASE_INSTANCE_NAME": os.getenv("LAKEBASE_INSTANCE_NAME", "NOT SET"),
            "DB_HOST": os.getenv("DB_HOST", "NOT SET"),
            "DB_USER": os.getenv("DB_USER", "NOT SET"),
            "DB_NAME": os.getenv("DB_NAME", "NOT SET"),
        },
        "token_manager_status": "NOT INITIALIZED",
        "workspace_client_status": "NOT INITIALIZED",
        "sp_credentials_status": "NOT FETCHED",
        "token_status": "NO TOKEN",
        "token_error": None,
        "database_status": "NOT CONNECTED",
    }
    
    if token_manager:
        result["token_manager_status"] = "INITIALIZED"
        
        if token_manager._workspace_client:
            result["workspace_client_status"] = "INITIALIZED"
        
        # Try to generate token using the workspace client
        try:
            token = token_manager.get_token()
            if token:
                result["token_status"] = f"GENERATED (length: {len(token)})"
                result["db_user"] = token_manager.db_user
            else:
                result["token_status"] = "NO TOKEN"
        except Exception as e:
            result["token_status"] = "GENERATION FAILED"
            result["token_error"] = str(e)
        
        # Try to test database connection
        try:
            from app.database import engine, refresh_engine
            
            # If engine is None, try to refresh it now that we have a token
            if engine is None:
                result["database_status"] = "ENGINE IS NONE - attempting refresh..."
                try:
                    refresh_engine()
                    from app.database import engine as new_engine
                    if new_engine:
                        from sqlalchemy import text
                        with new_engine.connect() as conn:
                            conn.execute(text("SELECT 1"))
                        result["database_status"] = "CONNECTED (after refresh)"
                except Exception as refresh_err:
                    result["database_status"] = f"REFRESH FAILED: {str(refresh_err)}"
            else:
                from sqlalchemy import text
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                result["database_status"] = "CONNECTED"
        except Exception as e:
            result["database_status"] = f"ERROR: {str(e)}"
    
    return result


@app.post("/api/v1/debug/database/refresh")
def debug_database_refresh():
    """Force refresh the database token and reconnect."""
    from app.database import refresh_engine
    from app.auth.token_manager import token_manager
    
    result = {
        "action": "refresh",
        "token_refresh": "NOT ATTEMPTED",
        "engine_refresh": "NOT ATTEMPTED",
        "status": "UNKNOWN"
    }
    
    # Step 1: Force token refresh
    if token_manager:
        try:
            # Clear existing token to force refresh
            token_manager._token = None
            token_manager._expires_at = None
            
            # Get new token
            new_token = token_manager.get_token()
            if new_token:
                result["token_refresh"] = f"SUCCESS (length: {len(new_token)})"
            else:
                result["token_refresh"] = "FAILED - no token returned"
        except Exception as e:
            result["token_refresh"] = f"FAILED: {str(e)}"
    else:
        result["token_refresh"] = "SKIPPED - token_manager not initialized"
    
    # Step 2: Show connection params before attempting
    if token_manager:
        try:
            params = token_manager.get_connection_params()
            result["connection_params"] = {
                "host": params.get("host", "?"),
                "port": params.get("port", "?"),
                "user": params.get("user", "?"),
                "dbname": params.get("dbname", "?"),
                "sslmode": params.get("sslmode", "?"),
                "password_length": len(params.get("password", "") or ""),
            }
        except Exception as e:
            result["connection_params"] = f"ERROR: {str(e)}"

    # Step 3: Refresh database engine
    try:
        success = refresh_engine()
        if success:
            result["engine_refresh"] = "SUCCESS"
            result["status"] = "CONNECTED"
        else:
            result["engine_refresh"] = "FAILED"
            result["status"] = "DISCONNECTED"
    except Exception as e:
        result["engine_refresh"] = f"ERROR: {str(e)}"
        result["status"] = "ERROR"
    
    return result



# =============================================================================
# Static File Serving for Combined Frontend + Backend Deployment
# Must be AFTER all API routes
# =============================================================================

# Path to static files (React build)
STATIC_DIR = Path(__file__).parent.parent / "static"

# Check if static directory exists (production deployment)
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    log_info(f"Static files found at {STATIC_DIR}, enabling SPA serving")
    
    # Mount static assets (JS, CSS, images)
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    
    # Mount static pricing data (for instant local calculations)
    PRICING_DIR = STATIC_DIR / "pricing"
    if PRICING_DIR.exists():
        app.mount("/static/pricing", StaticFiles(directory=PRICING_DIR), name="pricing")
        log_info(f"Pricing bundle found at {PRICING_DIR}")

    # Mount documentation site (Docusaurus build)
    DOCS_DIR = STATIC_DIR / "docs"
    if DOCS_DIR.exists():
        app.mount("/docs", StaticFiles(directory=DOCS_DIR, html=True), name="docs")
        log_info(f"Documentation site mounted at /docs/")
    
    # Serve static files at root (favicon, etc.)
    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = STATIC_DIR / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        return FileResponse(STATIC_DIR / "databricks-icon.svg")
    
    @app.get("/databricks-icon.svg")
    async def databricks_icon():
        return FileResponse(STATIC_DIR / "databricks-icon.svg")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_root():
        """Serve React SPA at root."""
        return FileResponse(STATIC_DIR / "index.html")
    
    # SPA catch-all handler - serve index.html for non-API routes
    # This must be the LAST route defined
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve React SPA for all non-API routes."""
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}, 404
        
        # Serve index.html for client-side routing
        return FileResponse(STATIC_DIR / "index.html")

else:
    log_info("Static files not found - running in API-only mode (local development)")
    
    # In local dev mode, serve API info at root
    @app.get("/")
    def root():
        """Root endpoint (local dev only)."""
        return {
            "name": "Lakemeter API",
            "version": "1.0.0",
            "description": "Databricks Pricing Calculator API",
            "mode": "API-only (frontend served separately)"
        }
