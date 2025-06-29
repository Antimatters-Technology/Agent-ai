"""
Document Upload API for VisaMate AI platform.
Simplified, reliable document handling with proper error handling.
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, validator

from src.core.config import settings
from src.adapters.aws_adapter import document_storage_service, metadata_storage_service

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


class DocumentType(str, Enum):
    """Supported document types for visa application."""
    # Application Forms
    IMM1294 = "imm1294"
    IMM5645 = "imm5645"
    IMM5257 = "imm5257"
    
    # Supporting Documents
    PASSPORT = "passport"
    ACCEPTANCE_LETTER = "acceptance_letter"
    EDUCATION_TRANSCRIPT = "education_transcript"
    IELTS_RESULTS = "ielts_results"
    GIC_PROOF = "gic_proof"
    TUITION_PAYMENT = "tuition_payment"
    PAL_TAL = "pal_tal"
    DIGITAL_PHOTO = "digital_photo"
    MEDICAL_EXAM = "medical_exam"
    
    # Optional Documents
    ADDITIONAL_DOCS = "additional_docs"
    CLIENT_INFO = "client_info"


class DocumentService:
    """Simplified document service with robust error handling."""
    
    def __init__(self):
        self.storage_service = document_storage_service
        self.metadata_service = metadata_storage_service
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def _generate_s3_key(self, session_id: str, document_id: str, file_name: str) -> str:
        """Generate S3 object key."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = file_name.replace(" ", "_").replace("/", "_")
        return f"documents/{session_id}/{document_id}/{timestamp}_{safe_filename}"
    
    async def generate_upload_url(self, session_id: str, document_type: str, 
                                 file_name: str, content_type: str, file_size: int) -> Dict[str, Any]:
        """Generate presigned URL for document upload."""
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Generate S3 key
            s3_key = self._generate_s3_key(session_id, document_id, file_name)
            
            # Create document metadata
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
            await self.metadata_service.store_document_metadata(metadata)
            
            # Generate presigned URL
            upload_url = await self.storage_service.generate_presigned_upload_url(
                key=s3_key,
                content_type=content_type,
                expires_in=3600
            )
            
            logger.info(f"Generated upload URL for document {document_id}")
            
            return {
                'document_id': document_id,
                'upload_url': upload_url,
                'expires_in': 3600,
                's3_key': s3_key,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate upload URL: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate upload URL: {str(e)}"
            )
    
    async def mark_upload_complete(self, document_id: str, file_size: int) -> Dict[str, Any]:
        """Mark document upload as complete."""
        try:
            # Get existing metadata
            metadata = await self.metadata_service.get_document_metadata(document_id)
            if not metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            
            # Update metadata
            metadata.update({
                'status': DocumentStatus.UPLOADED.value,
                'file_size': file_size,
                'uploaded_at': datetime.utcnow().isoformat()
            })
            
            # Save updated metadata
            await self.metadata_service.store_document_metadata(metadata)
            
            logger.info(f"Marked document {document_id} as uploaded")
            
            return {
                'document_id': document_id,
                'status': DocumentStatus.UPLOADED.value,
                'uploaded_at': metadata['uploaded_at']
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to mark upload complete: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete upload: {str(e)}"
            )
    
    async def list_documents(self, session_id: str) -> Dict[str, Any]:
        """List all documents for a session."""
        try:
            documents = await self.metadata_service.list_session_documents(session_id)
            
            # Calculate upload progress
            document_types = [doc.get('document_type') for doc in documents]
            uploaded_types = [
                doc.get('document_type') for doc in documents 
                if doc.get('status') in [DocumentStatus.UPLOADED.value, DocumentStatus.PROCESSED.value]
            ]
            
            upload_progress = {}
            for doc_type in DocumentType:
                upload_progress[doc_type.value] = doc_type.value in uploaded_types
            
            return {
                'session_id': session_id,
                'documents': documents,
                'total_count': len(documents),
                'upload_progress': upload_progress
            }
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list documents: {str(e)}"
            )
    
    async def get_download_url(self, document_id: str) -> Dict[str, Any]:
        """Get download URL for a document."""
        try:
            # Get document metadata
            metadata = await self.metadata_service.get_document_metadata(document_id)
            if not metadata:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            
            # Generate download URL
            download_url = await self.storage_service.generate_presigned_download_url(
                key=metadata['s3_key'],
                expires_in=3600
            )
            
            return {
                'document_id': document_id,
                'download_url': download_url,
                'expires_in': 3600,
                'file_name': metadata['file_name'],
                'content_type': metadata['content_type']
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get download URL: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get download URL: {str(e)}"
            )


# Global service instance
document_service = DocumentService()


# API Endpoints
@router.post("/init", response_model=Dict[str, Any], tags=["Documents"])
async def initialize_document_upload(data: Dict[str, Any]):
    """Initialize document upload and get presigned URL."""
    try:
        # Validate required fields
        required_fields = ['session_id', 'document_type', 'file_name', 'content_type', 'file_size']
        for field in required_fields:
            if field not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )
        
        # Validate file size (max 10MB)
        if data['file_size'] > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds 10MB limit"
            )
        
        # Validate file type
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.tiff', '.tif']
        if not any(data['file_name'].lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate upload URL
        result = await document_service.generate_upload_url(
            session_id=data['session_id'],
            document_type=data['document_type'],
            file_name=data['file_name'],
            content_type=data['content_type'],
            file_size=data['file_size']
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in document upload init: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/upload-complete", response_model=Dict[str, Any], tags=["Documents"])
async def mark_upload_complete(data: Dict[str, Any]):
    """Mark document upload as complete."""
    try:
        # Debug: Log the received data
        logger.info(f"Upload complete request received: {data}")
        
        # Validate required fields
        if 'document_id' not in data:
            logger.error(f"Missing document_id in payload: {data}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing document_id"
            )
        
        if 'file_size' not in data:
            logger.error(f"Missing file_size in payload: {data}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing file_size"
            )
        
        result = await document_service.mark_upload_complete(
            document_id=data['document_id'],
            file_size=data['file_size']
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload complete: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{session_id}", response_model=Dict[str, Any], tags=["Documents"])
async def list_session_documents(session_id: str):
    """List all documents for a session."""
    try:
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required"
            )
        
        result = await document_service.list_documents(session_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/download/{document_id}", response_model=Dict[str, Any], tags=["Documents"])
async def get_document_download_url(document_id: str):
    """Get download URL for a document."""
    try:
        if not document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="document_id is required"
            )
        
        result = await document_service.get_download_url(document_id)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) 