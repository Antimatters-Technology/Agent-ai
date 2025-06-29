"""
Health check endpoint for VisaMate AI platform.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from src.core.config import settings
from src.adapters.simple_aws import check_aws_health

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=Dict[str, Any], tags=["Health"])
async def health_check():
    """
    Health check endpoint that verifies service status.
    """
    try:
        # Check AWS connectivity
        aws_status = await check_aws_health()
        
        # System health
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT,
            "services": {
                "api": "healthy",
                "aws": aws_status,
                "database": "local_storage" if settings.ENVIRONMENT == "development" else "aws_dynamodb"
            },
            "configuration": {
                "aws_region": settings.AWS_REGION,
                "s3_bucket": settings.S3_BUCKET_NAME,
                "debug_mode": settings.DEBUG
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "services": {
                "api": "unhealthy"
            }
        }


@router.get("/status", response_model=Dict[str, Any], tags=["Health"])
async def status_check():
    """
    Simple status check endpoint.
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "VisaMate AI API is running"
    } 