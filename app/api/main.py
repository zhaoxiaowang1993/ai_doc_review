import sys
from pathlib import Path

# Ensure project root is on sys.path so `common` can be imported when running from app/api
API_DIR = Path(__file__).resolve().parent
APP_DIR = API_DIR.parent
ROOT_DIR = APP_DIR.parent  # project root containing `common`
# Put project roots at the front of sys.path to avoid shadowing by similarly named packages.
for p in (ROOT_DIR, APP_DIR):
    p_str = str(p)
    if p_str in sys.path:
        sys.path.remove(p_str)
    sys.path.insert(0, p_str)

from common.logger import get_logger
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from middleware.logging import LoggingMiddleware
from config.config import settings
from middleware.logging import LoggingMiddleware, setup_logging
from routers import issues, files, rules
from spa_staticfiles import SPAStaticFiles


# Set up logging configuration
setup_logging()

logging = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": settings.aad_client_id or None,
    },
)

# Add middlewares
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(issues.router)
app.include_router(files.router)
app.include_router(rules.router)


# Health check endpoint
@app.get(
    "/api/health",
    summary="Health Check",
    response_description="Health status of the API",
)
def health_check():
    logging.info("Health check endpoint called.")
    return Response(status_code=204)


# Mount the UI at the root path (should come last so it doesn't interfere with /api routes)
if settings.serve_static:
    static_dir = API_DIR / "www"
    if static_dir.exists():
        app.mount("/", SPAStaticFiles(directory=static_dir, html=True))
    else:
        logging.warning("Static directory 'www' not found. Set SERVE_STATIC=False or build UI into app/api/www.")


# Exception handler only for HTTPExceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logging.error(f"HTTPException occurred: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTPException", "message": exc.detail},
    )


# Exception handler for general exceptions
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unexpected error occurred: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "500 Internal Server Error",
            "message": str(exc),
        },
    )
