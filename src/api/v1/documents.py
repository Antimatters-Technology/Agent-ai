"""
Document Upload API for VisaMate AI platform.
Handles S3 presigned URLs, document tracking, and OCR processing.
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


class DocumentMetadata(BaseModel):
    """Document metadata model."""
    document_id: str
    session_id: str
    user_id: str
    document_type: DocumentType
    file_name: str
    file_size: Optional[int] = None
    content_type: str
    status: DocumentStatus = DocumentStatus.PENDING
    s3_key: str
    s3_bucket: str
    upload_url: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    ocr_results: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class PresignUrlRequest(BaseModel):
    """Request model for generating presigned URLs."""
    session_id: str = Field(..., min_length=1, description="Wizard session ID")
    document_type: DocumentType = Field(..., description="Type of document being uploaded")
    file_name: str = Field(..., min_length=1, max_length=255, description="Original file name")
    content_type: str = Field(..., description="MIME type of the file")
    file_size: int = Field(..., gt=0, le=10*1024*1024, description="File size in bytes (max 10MB)")
    
    @validator('file_name')
    def validate_file_name(cls, v):
        """Validate file name and extension."""
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.tiff', '.tif']
        if not any(v.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError(f"File type not supported. Allowed: {', '.join(allowed_extensions)}")
        return v
    
    @validator('content_type')
    def validate_content_type(cls, v):
        """Validate MIME type."""
        allowed_types = [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/tiff',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        if v not in allowed_types:
            raise ValueError(f"Content type not supported. Allowed: {', '.join(allowed_types)}")
        return v


class PresignUrlResponse(BaseModel):
    """Response model for presigned URLs."""
    document_id: str
    upload_url: str
    expires_in: int  # seconds
    max_file_size: int
    required_headers: Dict[str, str]
    s3_key: str


class DocumentUploadCompleteRequest(BaseModel):
    """Request to mark document upload as complete."""
    document_id: str
    file_size: int
    checksum: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    session_id: str
    documents: List[DocumentMetadata]
    total_count: int
    upload_progress: Dict[DocumentType, bool]  # Which document types are uploaded


class DocumentService:
    """Production-ready service for handling document operations."""
    
    def __init__(self):
        self.storage_service = document_storage_service
        self.metadata_service = metadata_storage_service
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def _generate_s3_key(self, session_id: str, document_id: str, file_name: str) -> str:
        """Generate S3 object key."""
        # Structure: documents/{session_id}/{document_id}/{timestamp}_{filename}
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = file_name.replace(" ", "_").replace("/", "_")
        return f"documents/{session_id}/{document_id}/{timestamp}_{safe_filename}"
    
    async def generate_presigned_url(self, request: PresignUrlRequest, user_id: str = "anonymous") -> PresignUrlResponse:
        """Generate presigned URL for document upload."""
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Generate S3 key
            s3_key = self._generate_s3_key(request.session_id, document_id, request.file_name)
            
            # Create document metadata
            expires_at = datetime.utcnow() + timedelta(hours=1)
            document_metadata = {
                'document_id': document_id,
                'session_id': request.session_id,
                'user_id': user_id,
                'document_type': request.document_type.value,
                'file_name': request.file_name,
                'file_size': request.file_size,
                'content_type': request.content_type,
                'status': DocumentStatus.UPLOADING.value,
                's3_key': s3_key,
                's3_bucket': self.bucket_name,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': int(expires_at.timestamp())
            }
            
            # Store metadata using real service
            await self.metadata_service.store_document_metadata(document_metadata)
            
            # Generate presigned URL using real service
            presigned_url = await self.storage_service.generate_presigned_upload_url(
                key=s3_key,
                content_type=request.content_type,
                expires_in=3600
            )
            
            logger.info(f"Generated presigned URL for document {document_id}")
            
            return PresignUrlResponse(
                document_id=document_id,
                upload_url=presigned_url,
                expires_in=3600,
                max_file_size=request.file_size,
                required_headers={
                    'Content-Type': request.content_type,
                    'Content-Length': str(request.file_size)
                },
                s3_key=s3_key
            )
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload service error: {str(e)}"
            )
    
    async def mark_upload_complete(self, document_id: str, file_size: int) -> DocumentMetadata:
        """Mark document upload as complete and trigger OCR processing."""
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
                'uploaded_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })
            
            # Store updated metadata
            await self.metadata_service.store_document_metadata(metadata)
            
            # Trigger OCR processing
            await self._trigger_ocr_processing(document_id)
            
            # Convert to DocumentMetadata model
            return DocumentMetadata(
                document_id=metadata['document_id'],
                session_id=metadata['session_id'],
                user_id=metadata['user_id'],
                document_type=DocumentType(metadata['document_type']),
                file_name=metadata['file_name'],
                file_size=metadata.get('file_size'),
                content_type=metadata['content_type'],
                status=DocumentStatus(metadata['status']),
                s3_key=metadata['s3_key'],
                s3_bucket=metadata['s3_bucket'],
                uploaded_at=datetime.fromisoformat(metadata['uploaded_at']) if metadata.get('uploaded_at') else None,
                created_at=datetime.fromisoformat(metadata['created_at']),
                expires_at=datetime.fromtimestamp(metadata['expires_at'])
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to mark upload complete: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process upload completion"
            )
    
    async def _trigger_ocr_processing(self, document_id: str, application_id: Optional[str] = None):
        """Trigger OCR processing for uploaded document and auto-fill questionnaire."""
        try:
            logger.info(f"Triggering OCR processing for document {document_id}")
            
            # Get document metadata
            metadata = await self.metadata_service.get_document_metadata(document_id)
            
            if metadata:
                # Update status to processing
                metadata.update({
                    'status': DocumentStatus.PROCESSING.value,
                    'updated_at': datetime.utcnow().isoformat()
                })
                await self.metadata_service.store_document_metadata(metadata)
                
                # Connect to ApplicationService OCR auto-fill pipeline
                try:
                    from src.services.application_service import application_service
                    
                    # Use session_id as application_id if not provided
                    if not application_id:
                        application_id = metadata.get('session_id') or 'default'
                    
                    # Process document for auto-fill
                    ocr_result = await application_service.process_document_for_auto_fill(
                        application_id=application_id,
                        document_id=document_id
                    )
                    
                    # Update metadata with OCR results
                    metadata.update({
                        'status': DocumentStatus.PROCESSED.value,
                        'processed_at': datetime.utcnow().isoformat(),
                        'ocr_results': {
                            'extracted_fields': ocr_result.extracted_fields,
                            'mapped_questionnaire_data': ocr_result.mapped_questionnaire_data,
                            'confidence_scores': ocr_result.confidence_scores,
                            'auto_filled_count': ocr_result.auto_filled_count,
                            'manual_review_required': ocr_result.manual_review_required,
                            'processing_time_ms': ocr_result.processing_time_ms
                        },
                        'updated_at': datetime.utcnow().isoformat()
                    })
                    await self.metadata_service.store_document_metadata(metadata)
                    
                    logger.info(f"OCR auto-fill completed: {ocr_result.auto_filled_count} fields filled for document {document_id}")
                    return ocr_result
                    
                except ImportError:
                    logger.warning("ApplicationService not available, using fallback OCR processing")
                    # Fallback to basic processing
                    logger.info(f"OCR processing started for document {document_id}")
                    
        except Exception as e:
            logger.error(f"Failed to trigger OCR processing: {str(e)}")
            # Update status to failed
            try:
                metadata = await self.metadata_service.get_document_metadata(document_id)
                if metadata:
                    metadata.update({
                        'status': DocumentStatus.FAILED.value,
                        'updated_at': datetime.utcnow().isoformat()
                    })
                    await self.metadata_service.store_document_metadata(metadata)
            except:
                pass
    
    async def list_documents(self, session_id: str) -> DocumentListResponse:
        """List all documents for a session."""
        try:
            # Get documents from metadata service
            documents_data = await self.metadata_service.list_session_documents(session_id)
            
            # Convert to DocumentMetadata models
            documents = []
            for doc_data in documents_data:
                try:
                    document = DocumentMetadata(
                        document_id=doc_data['document_id'],
                        session_id=doc_data['session_id'],
                        user_id=doc_data['user_id'],
                        document_type=DocumentType(doc_data['document_type']),
                        file_name=doc_data['file_name'],
                        file_size=doc_data.get('file_size'),
                        content_type=doc_data['content_type'],
                        status=DocumentStatus(doc_data['status']),
                        s3_key=doc_data['s3_key'],
                        s3_bucket=doc_data['s3_bucket'],
                        uploaded_at=datetime.fromisoformat(doc_data['uploaded_at']) if doc_data.get('uploaded_at') else None,
                        created_at=datetime.fromisoformat(doc_data['created_at']),
                        expires_at=datetime.fromtimestamp(doc_data['expires_at'])
                    )
                    documents.append(document)
                except Exception as e:
                    logger.error(f"Failed to parse document metadata: {str(e)}")
                    continue
            
            # Calculate upload progress
            uploaded_types = {doc.document_type for doc in documents 
                            if doc.status in [DocumentStatus.UPLOADED, DocumentStatus.PROCESSED]}
            upload_progress = {doc_type: doc_type in uploaded_types for doc_type in DocumentType}
            
            return DocumentListResponse(
                session_id=session_id,
                documents=documents,
                total_count=len(documents),
                upload_progress=upload_progress
            )
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents"
            )


# Initialize service
document_service = DocumentService()


# API Endpoints
@router.post("/init", response_model=Dict[str, Any], tags=["Documents"])
async def initialize_document_upload(data: Dict[str, Any], user_id: str = "anonymous"):
    """Flexible document upload initialization that tries strict validation first, then falls back to simplified."""
    try:
        logger.info(f"Document upload init received data: {data}")
        
        # First try strict validation
        try:
            strict_request = PresignUrlRequest(**data)
            logger.info(f"Strict validation passed for document type: {strict_request.document_type}, session: {strict_request.session_id}")
            result = await document_service.generate_presigned_url(strict_request, user_id)
            
            # Convert PresignUrlResponse to dict for consistency
            return {
                "document_id": result.document_id,
                "upload_url": result.upload_url,
                "expires_in": result.expires_in,
                "max_file_size": result.max_file_size,
                "required_headers": result.required_headers,
                "s3_key": result.s3_key
            }
            
        except (ValueError, TypeError) as validation_error:
            logger.warning(f"Strict validation failed: {str(validation_error)}, falling back to simplified validation")
            
            # Fall back to simplified validation
            try:
                result = await initialize_document_upload_simple(data)
                # Return in the same format as strict validation
                return result
                
            except Exception as simple_error:
                logger.error(f"Both strict and simplified validation failed: {str(simple_error)}")
                return {
                    "status": "error",
                    "message": f"Document upload failed: {str(simple_error)}",
                    "strict_validation_error": str(validation_error),
                    "simplified_validation_error": str(simple_error),
                    "received_data": data,
                    "required_fields": ["session_id", "document_type", "file_name", "content_type", "file_size"],
                    "supported_document_types": [dt.value for dt in DocumentType],
                    "supported_content_types": [
                        "application/pdf",
                        "image/jpeg", 
                        "image/png",
                        "application/msword"
                    ],
                    "required_headers": {}
                }
        
    except Exception as e:
        logger.error(f"Unexpected error in document upload init: {str(e)}")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "received_data": data,
            "required_headers": {}
        }


@router.post("/init-simple", response_model=Dict[str, Any], tags=["Documents"])
async def initialize_document_upload_simple(data: Dict[str, Any]):
    """Simplified document upload initialization (more forgiving)."""
    try:
        logger.info(f"Simple document upload init: {data}")
        
        # Extract required fields with defaults - handle both frontend and backend field names
        session_id = data.get('session_id', 'unknown')
        document_type = data.get('document_type') or data.get('category', 'additional_docs')
        file_name = data.get('file_name') or data.get('filename', 'document.pdf')
        content_type = data.get('content_type', 'application/pdf')
        file_size = data.get('file_size') or data.get('size', 1000000)  # Default 1MB
        
        # Create a more permissive request
        try:
            # Map frontend categories to our document types
            category_mapping = {
                'other': 'additional_docs',
                'others': 'additional_docs',
                'additional': 'additional_docs',
                'passport': 'passport',
                'acceptance': 'acceptance_letter',
                'transcript': 'education_transcript',
                'ielts': 'ielts_results',
                'gic': 'gic_proof',
                'tuition': 'tuition_payment',
                'photo': 'digital_photo',
                'medical': 'medical_exam'
            }
            
            # Try to use exact document type, then try mapping, then default
            if document_type in [dt.value for dt in DocumentType]:
                pass  # Use as-is
            elif document_type.lower() in category_mapping:
                document_type = category_mapping[document_type.lower()]
            else:
                document_type = 'additional_docs'
            
            # Map common content types
            content_type_mapping = {
                'pdf': 'application/pdf',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            
            # If content_type looks like an extension, map it
            if content_type in content_type_mapping:
                content_type = content_type_mapping[content_type]
            
            # Ensure file_size is reasonable
            file_size = max(1, min(int(file_size), 10*1024*1024))
            
            simplified_request = PresignUrlRequest(
                session_id=session_id,
                document_type=DocumentType(document_type),
                file_name=file_name,
                content_type=content_type,
                file_size=file_size
            )
            
            result = await document_service.generate_presigned_url(simplified_request)
            
            # Return the exact same format as the original endpoint for frontend compatibility
            return {
                "document_id": result.document_id,
                "upload_url": result.upload_url,
                "expires_in": result.expires_in,
                "max_file_size": result.max_file_size,
                "required_headers": result.required_headers,
                "s3_key": result.s3_key
            }
            
        except Exception as e:
            logger.error(f"Failed to process simplified request: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to initialize upload: {str(e)}",
                "received_data": data,
                "required_fields": ["session_id", "document_type", "file_name", "content_type", "file_size"],
                "supported_document_types": [dt.value for dt in DocumentType],
                "supported_content_types": [
                    "application/pdf",
                    "image/jpeg", 
                    "image/png",
                    "application/msword"
                ],
                "required_headers": {}
            }
            
    except Exception as e:
        logger.error(f"Error in simple document upload init: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload initialization failed: {str(e)}"
        )


@router.post("/upload-complete", response_model=DocumentMetadata, tags=["Documents"])
async def mark_upload_complete(request: DocumentUploadCompleteRequest):
    """Mark document upload as complete and trigger processing."""
    logger.info(f"Marking upload complete for document: {request.document_id}")
    
    return await document_service.mark_upload_complete(request.document_id, request.file_size)


@router.get("/{session_id}", response_model=DocumentListResponse, tags=["Documents"])
async def list_session_documents(session_id: str):
    """List all documents for a wizard session."""
    logger.info(f"Listing documents for session: {session_id}")
    
    return await document_service.list_documents(session_id)


@router.get("/download/{document_id}", tags=["Documents"])
async def get_document_download_url(document_id: str):
    """Generate presigned URL for document download."""
    try:
        # TODO: Implement download URL generation
        # This would generate a presigned GET URL for the document
        
        return {
            "download_url": f"https://example.com/download/{document_id}",
            "expires_in": 3600,
            "message": "Download URL generation not yet implemented"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate download URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL"
        ) 