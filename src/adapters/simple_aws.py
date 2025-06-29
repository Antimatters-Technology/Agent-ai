"""
Simplified AWS Services for VisaMate AI platform.
Clean, reliable implementation without complex async context managers.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from src.core.config import settings

logger = logging.getLogger(__name__)


class SimpleAWSClient:
    """Simple, reliable AWS client without complex async patterns."""
    
    def __init__(self):
        self.region = settings.AWS_REGION
        self.bucket_name = settings.S3_BUCKET_NAME
        self._s3_client = None
        self._dynamodb_resource = None
    
    @property
    def s3_client(self):
        """Get S3 client with lazy initialization."""
        if self._s3_client is None:
            try:
                self._s3_client = boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info("S3 client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
                raise
        return self._s3_client
    
    @property
    def dynamodb_resource(self):
        """Get DynamoDB resource with lazy initialization."""
        if self._dynamodb_resource is None:
            try:
                self._dynamodb_resource = boto3.resource(
                    'dynamodb',
                    region_name=self.region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info("DynamoDB resource initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize DynamoDB resource: {str(e)}")
                raise
        return self._dynamodb_resource
    
    def generate_presigned_url(self, s3_key: str, content_type: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for S3 upload."""
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            logger.info(f"Generated presigned URL for key: {s3_key}")
            return presigned_url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            raise
    
    def generate_download_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for S3 download."""
        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expires_in
            )
            logger.info(f"Generated download URL for key: {s3_key}")
            return presigned_url
        except ClientError as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise
    
    def check_s3_connectivity(self) -> bool:
        """Check S3 connectivity."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except Exception as e:
            logger.warning(f"S3 connectivity check failed: {str(e)}")
            return False


class SimpleDocumentStorage:
    """Simple document storage service."""
    
    def __init__(self):
        self.aws_client = SimpleAWSClient()
        self.local_storage_dir = "local_storage/documents"
        self.use_local = settings.ENVIRONMENT == "development"
        
        # Create local storage directory if needed
        if self.use_local:
            os.makedirs(self.local_storage_dir, exist_ok=True)
    
    async def generate_upload_url(self, s3_key: str, content_type: str) -> str:
        """Generate upload URL (S3 or local mock)."""
        try:
            if self.use_local or not self.aws_client.check_s3_connectivity():
                # Return mock URL for local development
                return f"http://localhost:8000/mock-upload/{s3_key}"
            
            return self.aws_client.generate_presigned_url(s3_key, content_type)
        except Exception as e:
            logger.error(f"Failed to generate upload URL: {str(e)}")
            # Fallback to mock URL
            return f"http://localhost:8000/mock-upload/{s3_key}"
    
    async def generate_download_url(self, s3_key: str) -> str:
        """Generate download URL (S3 or local)."""
        try:
            if self.use_local or not self.aws_client.check_s3_connectivity():
                # Return local file path or mock URL
                return f"http://localhost:8000/mock-download/{s3_key}"
            
            return self.aws_client.generate_download_url(s3_key)
        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            # Fallback to mock URL
            return f"http://localhost:8000/mock-download/{s3_key}"


class SimpleMetadataStorage:
    """Simple metadata storage service."""
    
    def __init__(self):
        self.aws_client = SimpleAWSClient()
        self.local_storage_dir = "local_storage/metadata"
        self.use_local = True  # Always use local for development
        
        # Create local storage directory
        os.makedirs(self.local_storage_dir, exist_ok=True)
    
    async def store_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Store document metadata."""
        try:
            document_id = metadata.get('document_id')
            if not document_id:
                raise ValueError("document_id is required")
            
            # Always store locally for reliability
            local_path = os.path.join(self.local_storage_dir, f"{document_id}.json")
            with open(local_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Stored metadata for document: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store metadata: {str(e)}")
            return False
    
    async def get_metadata(self, document_id: str) -> Dict[str, Any]:
        """Get document metadata."""
        try:
            local_path = os.path.join(self.local_storage_dir, f"{document_id}.json")
            if os.path.exists(local_path):
                with open(local_path, 'r') as f:
                    return json.load(f)
            
            logger.warning(f"Metadata not found for document: {document_id}")
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            return {}
    
    async def list_session_documents(self, session_id: str) -> List[Dict[str, Any]]:
        """List all documents for a session."""
        try:
            documents = []
            for filename in os.listdir(self.local_storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.local_storage_dir, filename)
                    with open(file_path, 'r') as f:
                        doc = json.load(f)
                        if doc.get('session_id') == session_id:
                            documents.append(doc)
            
            logger.info(f"Found {len(documents)} documents for session: {session_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list session documents: {str(e)}")
            return []


class SimpleWizardStorage:
    """Simple wizard storage service."""
    
    def __init__(self):
        self.local_storage_dir = "local_storage/wizard"
        os.makedirs(self.local_storage_dir, exist_ok=True)
    
    async def save_answers(self, session_id: str, answers: Dict[str, Any]) -> bool:
        """Save wizard answers."""
        try:
            file_path = os.path.join(self.local_storage_dir, f"{session_id}_answers.json")
            with open(file_path, 'w') as f:
                json.dump({
                    'session_id': session_id,
                    'answers': answers,
                    'updated_at': datetime.utcnow().isoformat()
                }, f, indent=2, default=str)
            
            logger.info(f"Saved wizard answers for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save wizard answers: {str(e)}")
            return False
    
    async def get_answers(self, session_id: str) -> Dict[str, Any]:
        """Get wizard answers."""
        try:
            file_path = os.path.join(self.local_storage_dir, f"{session_id}_answers.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    return data.get('answers', {})
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get wizard answers: {str(e)}")
            return {}


# Global service instances
simple_document_storage = SimpleDocumentStorage()
simple_metadata_storage = SimpleMetadataStorage()
simple_wizard_storage = SimpleWizardStorage()


async def check_aws_health() -> Dict[str, Any]:
    """Check AWS service health."""
    aws_client = SimpleAWSClient()
    
    return {
        's3_connected': aws_client.check_s3_connectivity(),
        'bucket_name': settings.S3_BUCKET_NAME,
        'region': settings.AWS_REGION,
        'local_storage': settings.ENVIRONMENT == "development"
    } 