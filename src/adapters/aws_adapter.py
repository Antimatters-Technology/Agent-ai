"""
Production-ready AWS Services Adapter for VisaMate AI platform.
Simple, reliable, and scalable AWS integration.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import uuid
import hashlib
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from boto3.dynamodb.conditions import Key, Attr

from src.core.config import settings

logger = logging.getLogger(__name__)


class AWSClientManager:
    """Singleton AWS client manager for efficient resource usage."""
    
    _instance = None
    _clients = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self, service_name: str, region: str = None):
        """Get or create AWS client."""
        region = region or settings.AWS_REGION
        client_key = f"{service_name}_{region}"
        
        if client_key not in self._clients:
            try:
                self._clients[client_key] = boto3.client(
                    service_name,
                    region_name=region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info(f"Created {service_name} client for region {region}")
            except Exception as e:
                logger.error(f"Failed to create {service_name} client: {str(e)}")
                raise
        
        return self._clients[client_key]
    
    def get_resource(self, service_name: str, region: str = None):
        """Get or create AWS resource."""
        region = region or settings.AWS_REGION
        resource_key = f"{service_name}_resource_{region}"
        
        if resource_key not in self._clients:
            try:
                self._clients[resource_key] = boto3.resource(
                    service_name,
                    region_name=region,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info(f"Created {service_name} resource for region {region}")
            except Exception as e:
                logger.error(f"Failed to create {service_name} resource: {str(e)}")
                raise
        
        return self._clients[resource_key]


# Global client manager instance
aws_client_manager = AWSClientManager()


class DocumentStorageService:
    """Production-ready S3 document storage service."""
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
    
    def _get_s3_client(self):
        """Get S3 client."""
        return aws_client_manager.get_client('s3', self.region)
    
    async def generate_presigned_upload_url(self, key: str, content_type: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for uploading to S3."""
        try:
            s3_client = self._get_s3_client()
            
            # Generate presigned PUT URL for direct upload
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned URL for key: {key}")
            return presigned_url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {str(e)}")
            raise
    
    async def generate_presigned_download_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for downloading from S3."""
        try:
            s3_client = self._get_s3_client()
            
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated download URL for key: {key}")
            return presigned_url
            
        except ClientError as e:
            logger.error(f"Failed to generate download URL for {key}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating download URL: {str(e)}")
            raise
    
    async def check_object_exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            s3_client = self._get_s3_client()
            s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
        except Exception as e:
            logger.error(f"Error checking object existence for {key}: {str(e)}")
            raise
    
    async def delete_object(self, key: str) -> bool:
        """Delete object from S3."""
        try:
            s3_client = self._get_s3_client()
            s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted object: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete object {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting object: {str(e)}")
            return False


class MetadataStorageService:
    """Production-ready DynamoDB metadata storage service."""
    
    def __init__(self):
        self.table_prefix = settings.DYNAMODB_TABLE_PREFIX
        self.region = settings.AWS_REGION
        self._tables = {}
    
    def _get_dynamodb_resource(self):
        """Get DynamoDB resource."""
        return aws_client_manager.get_resource('dynamodb', self.region)
    
    def _get_table_name(self, table_type: str) -> str:
        """Get full table name with prefix."""
        return f"{self.table_prefix}-{table_type}"
    
    def _get_table(self, table_type: str):
        """Get DynamoDB table."""
        table_name = self._get_table_name(table_type)
        if table_name not in self._tables:
            dynamodb = self._get_dynamodb_resource()
            self._tables[table_name] = dynamodb.Table(table_name)
        return self._tables[table_name]
    
    async def store_document_metadata(self, metadata: dict) -> bool:
        """Store document metadata in DynamoDB."""
        try:
            # Use local storage for development, DynamoDB for production
            if settings.ENVIRONMENT == "development":
                return await self._store_local_metadata(metadata)
            
            table = self._get_table('documents')
            
            # Add timestamp and TTL
            metadata['created_at'] = datetime.utcnow().isoformat()
            metadata['ttl'] = int((datetime.utcnow() + timedelta(days=30)).timestamp())
            
            table.put_item(Item=metadata)
            logger.info(f"Stored metadata for document: {metadata.get('document_id')}")
            return True
            
        except ClientError as e:
            logger.error(f"DynamoDB error storing metadata: {str(e)}")
            # Fallback to local storage
            return await self._store_local_metadata(metadata)
        except Exception as e:
            logger.error(f"Failed to store document metadata: {str(e)}")
            # Fallback to local storage
            return await self._store_local_metadata(metadata)
    
    async def get_document_metadata(self, document_id: str) -> dict:
        """Get document metadata from DynamoDB."""
        try:
            # Use local storage for development
            if settings.ENVIRONMENT == "development":
                return await self._get_local_metadata(document_id)
            
            table = self._get_table('documents')
            
            response = table.get_item(Key={'document_id': document_id})
            if 'Item' in response:
                return dict(response['Item'])
            return {}
            
        except ClientError as e:
            logger.error(f"DynamoDB error getting metadata: {str(e)}")
            # Fallback to local storage
            return await self._get_local_metadata(document_id)
        except Exception as e:
            logger.error(f"Failed to get document metadata: {str(e)}")
            # Fallback to local storage
            return await self._get_local_metadata(document_id)
    
    async def list_session_documents(self, session_id: str) -> list:
        """List all documents for a session."""
        try:
            # Use local storage for development
            if settings.ENVIRONMENT == "development":
                return await self._list_local_documents(session_id)
            
            table = self._get_table('documents')
            
            response = table.query(
                IndexName='session-id-index',
                KeyConditionExpression=Key('session_id').eq(session_id)
            )
            
            return [dict(item) for item in response.get('Items', [])]
            
        except ClientError as e:
            logger.error(f"DynamoDB error listing documents: {str(e)}")
            # Fallback to local storage
            return await self._list_local_documents(session_id)
        except Exception as e:
            logger.error(f"Failed to list session documents: {str(e)}")
            # Fallback to local storage
            return await self._list_local_documents(session_id)
    
    # Local storage fallback methods
    async def _store_local_metadata(self, metadata: dict) -> bool:
        """Store metadata locally for development."""
        try:
            import os
            import json
            
            # Create local storage directory
            storage_dir = "local_storage/documents"
            os.makedirs(storage_dir, exist_ok=True)
            
            # Save metadata to file
            file_path = os.path.join(storage_dir, f"{metadata['document_id']}.json")
            with open(file_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Stored metadata locally: {metadata['document_id']}")
            return True
        except Exception as e:
            logger.error(f"Failed to store local metadata: {str(e)}")
            return False
    
    async def _get_local_metadata(self, document_id: str) -> dict:
        """Get metadata from local storage."""
        try:
            import os
            import json
            
            file_path = f"local_storage/documents/{document_id}.json"
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to get local metadata: {str(e)}")
            return {}
    
    async def _list_local_documents(self, session_id: str) -> list:
        """List documents from local storage."""
        try:
            import os
            import json
            
            storage_dir = "local_storage/documents"
            if not os.path.exists(storage_dir):
                return []
            
            documents = []
            for filename in os.listdir(storage_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(storage_dir, filename)
                    with open(file_path, 'r') as f:
                        doc = json.load(f)
                        if doc.get('session_id') == session_id:
                            documents.append(doc)
            
            return documents
        except Exception as e:
            logger.error(f"Failed to list local documents: {str(e)}")
            return []


class WizardStorageService:
    """Production-ready wizard session storage service."""
    
    def __init__(self):
        self.table_prefix = settings.DYNAMODB_TABLE_PREFIX
        self.region = settings.AWS_REGION
    
    def _get_dynamodb_resource(self):
        """Get DynamoDB resource."""
        return aws_client_manager.get_resource('dynamodb', self.region)
    
    async def save_wizard_answers(self, session_id: str, answers: dict) -> bool:
        """Save wizard answers."""
        try:
            # Use local storage for development
            if settings.ENVIRONMENT == "development":
                return await self._save_local_answers(session_id, answers)
            
            dynamodb = self._get_dynamodb_resource()
            table = dynamodb.Table(f"{self.table_prefix}-wizard-sessions")
            
            # Update session with answers
            table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET answers = :answers, updated_at = :updated_at',
                ExpressionAttributeValues={
                    ':answers': answers,
                    ':updated_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Saved wizard answers for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save wizard answers: {str(e)}")
            # Fallback to local storage
            return await self._save_local_answers(session_id, answers)
    
    async def get_wizard_answers(self, session_id: str) -> dict:
        """Get wizard answers."""
        try:
            # Use local storage for development
            if settings.ENVIRONMENT == "development":
                return await self._get_local_answers(session_id)
            
            dynamodb = self._get_dynamodb_resource()
            table = dynamodb.Table(f"{self.table_prefix}-wizard-sessions")
            
            response = table.get_item(Key={'session_id': session_id})
            if 'Item' in response:
                return response['Item'].get('answers', {})
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get wizard answers: {str(e)}")
            # Fallback to local storage
            return await self._get_local_answers(session_id)
    
    async def _save_local_answers(self, session_id: str, answers: dict) -> bool:
        """Save answers locally for development."""
        try:
            import os
            import json
            
            storage_dir = "local_storage/wizard"
            os.makedirs(storage_dir, exist_ok=True)
            
            file_path = os.path.join(storage_dir, f"{session_id}_answers.json")
            with open(file_path, 'w') as f:
                json.dump(answers, f, indent=2, default=str)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save local answers: {str(e)}")
            return False
    
    async def _get_local_answers(self, session_id: str) -> dict:
        """Get answers from local storage."""
        try:
            import os
            import json
            
            file_path = f"local_storage/wizard/{session_id}_answers.json"
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Failed to get local answers: {str(e)}")
            return {}


# Global service instances
document_storage_service = DocumentStorageService()
metadata_storage_service = MetadataStorageService()
wizard_storage_service = WizardStorageService()


# Health check function
async def check_aws_connectivity() -> Dict[str, Any]:
    """Check AWS service connectivity."""
    status = {
        's3': False,
        'dynamodb': False,
        'region': settings.AWS_REGION,
        'bucket': settings.S3_BUCKET_NAME
    }
    
    try:
        # Test S3 connectivity
        s3_client = aws_client_manager.get_client('s3')
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        status['s3'] = True
        logger.info("S3 connectivity: OK")
    except Exception as e:
        logger.warning(f"S3 connectivity failed: {str(e)}")
    
    try:
        # Test DynamoDB connectivity
        dynamodb = aws_client_manager.get_resource('dynamodb')
        list(dynamodb.tables.all())  # This will fail if no permissions
        status['dynamodb'] = True
        logger.info("DynamoDB connectivity: OK")
    except Exception as e:
        logger.warning(f"DynamoDB connectivity failed: {str(e)}")
    
    return status 