"""
Simplified Document Upload API for VisaMate AI platform.
Reliable, error-free implementation with proper fallbacks.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.adapters.simple_aws import simple_document_storage, simple_metadata_storage
from src.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class SimpleDocumentService:
    """Simplified document service with robust error handling."""
    
    def __init__(self):
        self.storage = simple_document_storage
        self.metadata = simple_metadata_storage
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def _generate_s3_key(self, session_id: str, document_id: str, file_name: str) -> str:
        """Generate S3 object key."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = file_name.replace(" ", "_").replace("/", "_")
        return f"documents/{session_id}/{document_id}/{timestamp}_{safe_filename}"
    
    async def init_upload(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize document upload."""
        try:
            # Extract and validate data
            session_id = request_data.get('session_id', '')
            document_type = request_data.get('document_type', 'unknown')
            file_name = request_data.get('file_name', 'unknown.pdf')
            content_type = request_data.get('content_type', 'application/pdf')
            file_size = request_data.get('file_size', 0)
            
            if not session_id:
                raise ValueError("session_id is required")
            
            # Generate document ID and S3 key
            document_id = str(uuid.uuid4())
            s3_key = self._generate_s3_key(session_id, document_id, file_name)
            
            # Create metadata
            metadata = {
                'document_id': document_id,
                'session_id': session_id,
                'document_type': document_type,
                'file_name': file_name,
                'file_size': file_size,
                'content_type': content_type,
                'status': DocumentStatus.UPLOADING.value,
                's3_key': s3_key,
                's3_bucket': self.bucket_name,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
            }
            
            # Store metadata
            await self.metadata.store_metadata(metadata)
            
            # Generate upload URL
            upload_url = await self.storage.generate_upload_url(s3_key, content_type)
            
            logger.info(f"Initialized upload for document {document_id}")
            
            return {
                'success': True,
                'document_id': document_id,
                'upload_url': upload_url,
                'expires_in': 3600,
                's3_key': s3_key,
                'status': DocumentStatus.UPLOADING.value,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize upload: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'document_id': None,
                'upload_url': None
            }
    
    async def complete_upload(self, document_id: str, file_size: int) -> Dict[str, Any]:
        """Mark document upload as complete."""
        try:
            # Get existing metadata
            metadata = await self.metadata.get_metadata(document_id)
            if not metadata:
                raise ValueError(f"Document {document_id} not found")
            
            # Update metadata
            metadata.update({
                'status': DocumentStatus.UPLOADED.value,
                'file_size': file_size,
                'uploaded_at': datetime.utcnow().isoformat()
            })
            
            # Save updated metadata
            await self.metadata.store_metadata(metadata)
            
            logger.info(f"Completed upload for document {document_id}")
            
            return {
                'success': True,
                'document_id': document_id,
                'status': DocumentStatus.UPLOADED.value,
                'uploaded_at': metadata['uploaded_at']
            }
            
        except Exception as e:
            logger.error(f"Failed to complete upload: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id
            }
    
    async def list_documents(self, session_id: str) -> Dict[str, Any]:
        """List all documents for a session."""
        try:
            documents = await self.metadata.list_session_documents(session_id)
            
            # Calculate progress
            uploaded_count = sum(1 for doc in documents if doc.get('status') == DocumentStatus.UPLOADED.value)
            
            return {
                'success': True,
                'session_id': session_id,
                'documents': documents,
                'total_count': len(documents),
                'uploaded_count': uploaded_count,
                'progress': f"{uploaded_count}/{len(documents)}" if documents else "0/0"
            }
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'session_id': session_id,
                'documents': []
            }
    
    async def get_download_url(self, document_id: str) -> Dict[str, Any]:
        """Get download URL for a document."""
        try:
            # Get document metadata
            metadata = await self.metadata.get_metadata(document_id)
            if not metadata:
                raise ValueError(f"Document {document_id} not found")
            
            # Generate download URL
            download_url = await self.storage.generate_download_url(metadata['s3_key'])
            
            return {
                'success': True,
                'document_id': document_id,
                'download_url': download_url,
                'expires_in': 3600,
                'file_name': metadata['file_name'],
                'content_type': metadata['content_type']
            }
            
        except Exception as e:
            logger.error(f"Failed to get download URL: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'document_id': document_id
            }


# Global service instance
doc_service = SimpleDocumentService()


# API Endpoints
@router.post("/init", tags=["Documents"])
async def init_document_upload(data: Dict[str, Any]):
    """Initialize document upload."""
    try:
        result = await doc_service.init_upload(data)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Unknown error')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in init_document_upload: {str(e)}")
        return {
            'success': False,
            'error': f"Internal server error: {str(e)}",
            'document_id': None,
            'upload_url': None
        }


@router.post("/upload-complete", tags=["Documents"])
async def complete_document_upload(data: Dict[str, Any]):
    """Complete document upload."""
    try:
        document_id = data.get('document_id')
        file_size = data.get('file_size', 0)
        
        if not document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="document_id is required"
            )
        
        result = await doc_service.complete_upload(document_id, file_size)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Unknown error')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in complete_document_upload: {str(e)}")
        return {
            'success': False,
            'error': f"Internal server error: {str(e)}",
            'document_id': data.get('document_id')
        }


@router.get("/{session_id}", tags=["Documents"])
async def list_session_documents(session_id: str):
    """List all documents for a session."""
    try:
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required"
            )
        
        result = await doc_service.list_documents(session_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in list_session_documents: {str(e)}")
        return {
            'success': False,
            'error': f"Internal server error: {str(e)}",
            'session_id': session_id,
            'documents': []
        }


@router.get("/download/{document_id}", tags=["Documents"])
async def get_download_url(document_id: str):
    """Get download URL for a document."""
    try:
        if not document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="document_id is required"
            )
        
        result = await doc_service.get_download_url(document_id)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.get('error', 'Document not found')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_download_url: {str(e)}")
        return {
            'success': False,
            'error': f"Internal server error: {str(e)}",
            'document_id': document_id
        } 