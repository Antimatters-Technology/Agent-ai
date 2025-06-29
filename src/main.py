"""
VisaMate AI - Main FastAPI Application
Production-ready Canada Study Visa AI platform with AWS integration.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvicorn

from src.core.config import settings
from src.api.v1.wizard import router as wizard_router
from src.api.v1.documents import router as documents_router
from src.api.v1.documents_simple import router as documents_simple_router
from src.api.v1.health import router as health_router
from src.services.gemini_service import gemini_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log') if settings.ENVIRONMENT == 'production' else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting VisaMate AI application...")
    
    try:
        # Initialize AWS services
        logger.info("Initializing AWS services...")
        
        # Test AWS connectivity
        await test_aws_connectivity()
        
        # Initialize Gemini service
        logger.info("Initializing Gemini AI service...")
        
        # Load any required data or models
        await load_application_data()
        
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down VisaMate AI application...")
    await cleanup_resources()
    logger.info("Application shutdown completed")


async def test_aws_connectivity():
    """Test connectivity to AWS services."""
    try:
        # AWS connectivity tests will be implemented when adapters are ready
        logger.info("AWS services configured")
            
    except Exception as e:
        logger.error(f"AWS connectivity test failed: {str(e)}")
        # In production, you might want to fail gracefully or use fallback services
        if settings.ENVIRONMENT == 'production':
            raise


async def load_application_data():
    """Load required application data and configurations."""
    try:
        # Load SOP templates, validation rules, etc.
        logger.info("Loading application data...")
        
        # Initialize any caches or pre-computed data
        
        logger.info("Application data loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load application data: {str(e)}")
        raise


async def cleanup_resources():
    """Cleanup resources during shutdown."""
    try:
        # Close any open connections, clear caches, etc.
        logger.info("Cleaning up resources...")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Canada Study Visa application platform",
    version=settings.API_VERSION,
    openapi_url=f"/api/{settings.API_VERSION}/openapi.json" if settings.DEBUG else None,
    docs_url=f"/api/{settings.API_VERSION}/docs" if settings.DEBUG else None,
    redoc_url=f"/api/{settings.API_VERSION}/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
    debug=settings.DEBUG
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["visamate.ai", "*.visamate.ai"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with detailed error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error",
                "timestamp": "2024-01-01T00:00:00Z",
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors with user-friendly messages."""
    logger.error(f"Value error in {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": 400,
                "message": str(exc),
                "type": "validation_error",
                "timestamp": "2024-01-01T00:00:00Z",
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with error logging."""
    logger.error(f"Unhandled exception in {request.url.path}: {str(exc)}", exc_info=True)
    
    if settings.DEBUG:
        error_detail = str(exc)
    else:
        error_detail = "An internal server error occurred"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": error_detail,
                "type": "internal_error",
                "timestamp": "2024-01-01T00:00:00Z",
                "path": str(request.url.path)
            }
        }
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with service status."""
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {}
    }
    
    # Check AWS services (placeholder for when adapters are implemented)
    health_status["services"]["dynamodb"] = "configured"
    health_status["services"]["s3"] = "configured"
    health_status["services"]["cognito"] = "configured"
    
    # Check Gemini service
    try:
        health_status["services"]["gemini"] = "configured" if settings.GEMINI_API_KEY else "not_configured"
    except Exception as e:
        health_status["services"]["gemini"] = f"error: {str(e)}"
    
    return health_status


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to VisaMate AI",
        "description": "AI-powered Canada Study Visa application platform",
        "version": settings.API_VERSION,
        "documentation": f"/api/{settings.API_VERSION}/docs" if settings.DEBUG else None,
        "health_check": "/health"
    }


# API version info
@app.get(f"/api/{settings.API_VERSION}", tags=["API Info"])
async def api_info():
    """API version information."""
    return {
        "api_version": settings.API_VERSION,
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "features": {
            "sop_generation": True,
            "document_processing": True,
            "wizard_flow": True,
            "ai_powered": True,
            "aws_integration": True
        },
        "endpoints": {
            "wizard": f"/api/{settings.API_VERSION}/wizard",
            "documents": f"/api/{settings.API_VERSION}/documents",
            "eligibility": f"/api/{settings.API_VERSION}/eligibility",
            "forms": f"/api/{settings.API_VERSION}/forms",
            "portal": f"/api/{settings.API_VERSION}/portal",
            "consultant": f"/api/{settings.API_VERSION}/consultant",
            "rag": f"/api/{settings.API_VERSION}/rag",
            "billing": f"/api/{settings.API_VERSION}/billing",
            "whatsapp": f"/api/{settings.API_VERSION}/whatsapp"
        }
    }


# Include API routers
app.include_router(
    wizard_router,
    prefix=f"/api/{settings.API_VERSION}/wizard",
    tags=["Wizard"]
)

app.include_router(
    documents_router,
    prefix=f"/api/{settings.API_VERSION}/documents",
    tags=["Documents"]
)

app.include_router(
    documents_simple_router,
    prefix=f"/api/{settings.API_VERSION}/documents-simple",
    tags=["Documents-Simple"]
)

app.include_router(
    health_router,
    prefix=f"/api/{settings.API_VERSION}",
    tags=["Health-Extended"]
)

# Add fallback routes for frontend URL issues (duplicate /api/v1/)
@app.post("/api/v1/api/v1/wizard/start", tags=["Fallback"])
async def fallback_wizard_start():
    """Fallback route for frontend URL duplication issue."""
    from fastapi import Depends
    from src.api.v1.wizard import start_wizard_session
    logger.warning("Frontend called duplicate URL: /api/v1/api/v1/wizard/start - redirecting to correct endpoint")
    return await start_wizard_session()

@app.get("/api/v1/api/v1/wizard/tree/{session_id}", tags=["Fallback"])
async def fallback_wizard_tree(session_id: str):
    """Fallback route for frontend URL duplication issue."""
    from src.api.v1.wizard import get_wizard_tree
    logger.warning(f"Frontend called duplicate URL: /api/v1/api/v1/wizard/tree/{session_id} - redirecting to correct endpoint")
    return await get_wizard_tree(session_id)

@app.get("/api/v1/api/v1/wizard/document-checklist/{session_id}", tags=["Fallback"])
async def fallback_document_checklist(session_id: str):
    """Fallback route for frontend URL duplication issue."""
    from src.api.v1.wizard import get_document_checklist
    logger.warning(f"Frontend called duplicate URL: /api/v1/api/v1/wizard/document-checklist/{session_id} - redirecting to correct endpoint")
    return await get_document_checklist(session_id)

@app.post("/api/v1/api/v1/wizard/questionnaire/{session_id}", tags=["Fallback"])
async def fallback_questionnaire(session_id: str, answers: dict):
    """Fallback route for frontend URL duplication issue."""
    from src.api.v1.wizard import submit_questionnaire_answers
    logger.warning(f"Frontend called duplicate URL: /api/v1/api/v1/wizard/questionnaire/{session_id} - redirecting to correct endpoint")
    return await submit_questionnaire_answers(session_id, answers)

@app.post("/api/v1/api/v1/documents/init", tags=["Fallback"])
async def fallback_documents_init(data: dict):
    """Fallback route for frontend URL duplication issue."""
    from src.api.v1.documents import initialize_document_upload_simple
    logger.warning(f"Frontend called duplicate URL: /api/v1/api/v1/documents/init - redirecting to simple endpoint")
    return await initialize_document_upload_simple(data)

# WebSocket stub (to stop 403 errors)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Basic WebSocket endpoint stub to prevent frontend errors."""
    logger.info("WebSocket connection attempted - accepting and closing gracefully")
    try:
        await websocket.accept()
        await websocket.send_text('{"type":"info","message":"WebSocket not implemented yet"}')
        await websocket.close()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

# Debug endpoint to test frontend connectivity
@app.get("/debug/endpoints", tags=["Debug"])
async def debug_endpoints():
    """Debug endpoint showing all available routes."""
    routes_info = []
    for route in app.routes:
        if hasattr(route, 'methods'):
            routes_info.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {
        "message": "Available API endpoints",
        "base_url": "http://localhost:8000",
        "correct_urls": {
            "wizard_start": "POST http://localhost:8000/api/v1/wizard/start",
            "wizard_tree": "GET http://localhost:8000/api/v1/wizard/tree/{session_id}",
            "document_init": "POST http://localhost:8000/api/v1/documents/init",
            "health": "GET http://localhost:8000/health"
        },
        "routes": routes_info
    }


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.API_VERSION,
        description="AI-powered Canada Study Visa application platform with comprehensive document generation and processing capabilities.",
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        },
        "CognitoAuth": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/oauth2/authorize",
                    "tokenUrl": f"https://cognito-idp.{settings.AWS_REGION}.amazonaws.com/{settings.COGNITO_USER_POOL_ID}/oauth2/token",
                    "scopes": {
                        "email": "Email access",
                        "openid": "OpenID Connect",
                        "profile": "Profile access"
                    }
                }
            }
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Production server configuration
if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        workers=1 if settings.DEBUG else 4
    ) 