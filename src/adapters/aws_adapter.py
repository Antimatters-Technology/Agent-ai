"""
AWS Services Adapter for VisaMate AI platform.
Provides production-ready adapters for DynamoDB, S3, and Cognito services.
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
import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError
from boto3.dynamodb.conditions import Key, Attr

from src.core.config import settings

logger = logging.getLogger(__name__)


class DynamoDBAdapter:
    """Production-ready DynamoDB adapter with best practices."""
    
    def __init__(self):
        self.region = settings.AWS_REGION
        self.table_prefix = settings.DYNAMODB_TABLE_PREFIX
        self.session = None
        self._tables = {}
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aioboto3.Session()
        self.dynamodb = await self.session.resource(
            'dynamodb',
            region_name=self.region
        ).__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.dynamodb:
            await self.dynamodb.__aexit__(exc_type, exc_val, exc_tb)
    
    def _get_table_name(self, table_type: str) -> str:
        """Get full table name with prefix."""
        return f"{self.table_prefix}-{table_type}"
    
    async def _get_table(self, table_type: str):
        """Get DynamoDB table resource."""
        table_name = self._get_table_name(table_type)
        if table_name not in self._tables:
            self._tables[table_name] = await self.dynamodb.Table(table_name)
        return self._tables[table_name]
    
    async def create_user_profile(self, user_data: Dict[str, Any]) -> str:
        """Create a new user profile."""
        try:
            table = await self._get_table('users')
            user_id = str(uuid.uuid4())
            
            item = {
                'user_id': user_id,
                'email': user_data.get('email'),
                'full_name': user_data.get('full_name'),
                'nationality': user_data.get('nationality'),
                'phone': user_data.get('phone'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'profile_status': 'active',
                'subscription_tier': 'free',
                'applications_count': 0
            }
            
            # Add optional fields if present
            optional_fields = [
                'age', 'current_location', 'highest_qualification',
                'field_of_study', 'work_experience_years'
            ]
            for field in optional_fields:
                if field in user_data:
                    item[field] = user_data[field]
            
            await table.put_item(Item=item)
            logger.info(f"Created user profile: {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Failed to create user profile: {str(e)}")
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID."""
        try:
            table = await self._get_table('users')
            response = await table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                return dict(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user profile {user_id}: {str(e)}")
            raise
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile."""
        try:
            table = await self._get_table('users')
            
            # Build update expression
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.utcnow().isoformat()}
            
            for key, value in updates.items():
                if key not in ['user_id', 'created_at']:  # Protect immutable fields
                    update_expression += f", {key} = :{key}"
                    expression_values[f":{key}"] = value
            
            await table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Updated user profile: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user profile {user_id}: {str(e)}")
            raise
    
    async def create_wizard_session(self, user_id: str, session_data: Dict[str, Any]) -> str:
        """Create a new wizard session."""
        try:
            table = await self._get_table('wizard-sessions')
            session_id = str(uuid.uuid4())
            
            # Session expires in 24 hours
            expires_at = int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            
            item = {
                'session_id': session_id,
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'expires_at': expires_at,
                'current_step': session_data.get('current_step', 1),
                'total_steps': session_data.get('total_steps', 10),
                'session_data': session_data.get('session_data', {}),
                'status': 'active'
            }
            
            await table.put_item(Item=item)
            logger.info(f"Created wizard session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create wizard session: {str(e)}")
            raise
    
    async def get_wizard_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get wizard session."""
        try:
            table = await self._get_table('wizard-sessions')
            response = await table.get_item(
                Key={'session_id': session_id, 'user_id': user_id}
            )
            
            if 'Item' in response:
                return dict(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Failed to get wizard session {session_id}: {str(e)}")
            raise
    
    async def update_wizard_session(self, session_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update wizard session."""
        try:
            table = await self._get_table('wizard-sessions')
            
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': datetime.utcnow().isoformat()}
            
            for key, value in updates.items():
                if key not in ['session_id', 'user_id', 'created_at']:
                    update_expression += f", {key} = :{key}"
                    expression_values[f":{key}"] = value
            
            await table.update_item(
                Key={'session_id': session_id, 'user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update wizard session {session_id}: {str(e)}")
            raise
    
    async def save_sop_document(self, user_id: str, sop_data: Dict[str, Any]) -> str:
        """Save SOP document."""
        try:
            table = await self._get_table('sop-documents')
            document_id = str(uuid.uuid4())
            
            item = {
                'document_id': document_id,
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'sop_content': sop_data.get('sop_content', ''),
                'word_count': sop_data.get('word_count', 0),
                'quality_score': Decimal(str(sop_data.get('quality_score', 0))),
                'template_used': sop_data.get('template_used', 'standard'),
                'context_hash': sop_data.get('context_hash', ''),
                'status': 'generated',
                'version': 1
            }
            
            await table.put_item(Item=item)
            logger.info(f"Saved SOP document: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to save SOP document: {str(e)}")
            raise
    
    async def get_user_sop_documents(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's SOP documents."""
        try:
            table = await self._get_table('sop-documents')
            response = await table.query(
                IndexName='user_id-created_at-index',  # Assumes GSI exists
                KeyConditionExpression=Key('user_id').eq(user_id),
                ScanIndexForward=False,  # Most recent first
                Limit=limit
            )
            
            return [dict(item) for item in response.get('Items', [])]
            
        except Exception as e:
            logger.error(f"Failed to get SOP documents for user {user_id}: {str(e)}")
            raise


class S3Adapter:
    """Production-ready S3 adapter for document storage."""
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aioboto3.Session()
        self.s3 = await self.session.client('s3', region_name=self.region).__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.s3:
            await self.s3.__aexit__(exc_type, exc_val, exc_tb)
    
    def _generate_object_key(self, user_id: str, file_type: str, filename: str) -> str:
        """Generate S3 object key with proper structure."""
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')
        file_hash = hashlib.md5(f"{user_id}{filename}{datetime.utcnow()}".encode()).hexdigest()[:8]
        return f"{file_type}/{user_id}/{timestamp}/{file_hash}_{filename}"
    
    async def upload_document(self, user_id: str, file_content: bytes, 
                            filename: str, content_type: str) -> str:
        """Upload document to S3."""
        try:
            object_key = self._generate_object_key(user_id, 'documents', filename)
            
            await self.s3.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'user_id': user_id,
                    'original_filename': filename,
                    'upload_timestamp': datetime.utcnow().isoformat()
                },
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Uploaded document: {object_key}")
            return object_key
            
        except Exception as e:
            logger.error(f"Failed to upload document: {str(e)}")
            raise
    
    async def upload_sop(self, user_id: str, sop_content: str, document_id: str) -> str:
        """Upload SOP document to S3."""
        try:
            object_key = self._generate_object_key(user_id, 'sop', f"{document_id}.txt")
            
            await self.s3.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=sop_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'user_id': user_id,
                    'document_id': document_id,
                    'document_type': 'sop',
                    'upload_timestamp': datetime.utcnow().isoformat()
                },
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Uploaded SOP: {object_key}")
            return object_key
            
        except Exception as e:
            logger.error(f"Failed to upload SOP: {str(e)}")
            raise
    
    async def get_download_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for downloading."""
        try:
            url = await self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expires_in
            )
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise
    
    async def delete_document(self, object_key: str) -> bool:
        """Delete document from S3."""
        try:
            await self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Deleted document: {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            raise


class CognitoAdapter:
    """Production-ready Cognito adapter for authentication."""
    
    def __init__(self):
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.client_id = settings.COGNITO_CLIENT_ID
        self.region = settings.AWS_REGION
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aioboto3.Session()
        self.cognito = await self.session.client(
            'cognito-idp', 
            region_name=self.region
        ).__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.cognito:
            await self.cognito.__aexit__(exc_type, exc_val, exc_tb)
    
    async def create_user(self, email: str, password: str, user_attributes: Dict[str, str]) -> str:
        """Create a new user in Cognito."""
        try:
            # Prepare user attributes
            attributes = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'false'}
            ]
            
            for key, value in user_attributes.items():
                if key not in ['email']:  # Avoid duplicates
                    attributes.append({'Name': key, 'Value': str(value)})
            
            response = await self.cognito.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=attributes,
                TemporaryPassword=password,
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            # Set permanent password
            await self.cognito.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
                Password=password,
                Permanent=True
            )
            
            user_sub = response['User']['Username']
            logger.info(f"Created Cognito user: {user_sub}")
            return user_sub
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise ValueError("User already exists")
            else:
                logger.error(f"Cognito user creation failed: {str(e)}")
                raise
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens."""
        try:
            response = await self.cognito.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            if 'AuthenticationResult' in response:
                return {
                    'access_token': response['AuthenticationResult']['AccessToken'],
                    'id_token': response['AuthenticationResult']['IdToken'],
                    'refresh_token': response['AuthenticationResult']['RefreshToken'],
                    'expires_in': response['AuthenticationResult']['ExpiresIn']
                }
            else:
                raise ValueError("Authentication failed")
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['NotAuthorizedException', 'UserNotFoundException']:
                raise ValueError("Invalid credentials")
            else:
                logger.error(f"Cognito authentication failed: {str(e)}")
                raise
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from access token."""
        try:
            response = await self.cognito.get_user(AccessToken=access_token)
            
            user_info = {
                'username': response['Username'],
                'user_status': response['UserStatus'],
                'attributes': {}
            }
            
            for attr in response['UserAttributes']:
                user_info['attributes'][attr['Name']] = attr['Value']
            
            return user_info
            
        except ClientError as e:
            logger.error(f"Failed to get user info: {str(e)}")
            raise
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        try:
            response = await self.cognito.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            return {
                'access_token': response['AuthenticationResult']['AccessToken'],
                'id_token': response['AuthenticationResult']['IdToken'],
                'expires_in': response['AuthenticationResult']['ExpiresIn']
            }
            
        except ClientError as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise


# Global adapter instances
dynamodb_adapter = DynamoDBAdapter()
s3_adapter = S3Adapter()
cognito_adapter = CognitoAdapter()


# Helper functions for direct client access
async def get_s3_client():
    """Get S3 client for direct operations."""
    try:
        # For development without AWS credentials, use local/mock setup
        if settings.ENVIRONMENT == "development" and not settings.AWS_ACCESS_KEY_ID:
            logger.info("Using development S3 client (no real AWS)")
            # Return a mock-like object that has the methods we need
            import boto3
            from moto import mock_s3
            
            # Create a real boto3 client but with fake credentials for testing
            return boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id='testing',
                aws_secret_access_key='testing',
                endpoint_url='http://localhost:9000' if settings.ENVIRONMENT == "development" else None
            )
        
        # Production: Use real AWS credentials
        session = aioboto3.Session()
        async with session.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        ) as client:
            return client
            
    except Exception as e:
        logger.error(f"Failed to create S3 client: {str(e)}")
        # For development, return a working local client
        if settings.ENVIRONMENT == "development":
            import boto3
            return boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id='testing',
                aws_secret_access_key='testing'
            )
        raise


async def get_dynamodb_resource():
    """Get DynamoDB resource for direct operations."""
    try:
        # For development without AWS credentials  
        if settings.ENVIRONMENT == "development" and not settings.AWS_ACCESS_KEY_ID:
            logger.info("Using development DynamoDB (no real AWS)")
            # Return None to skip database operations in development
            return None
        
        # Production: Use real AWS credentials
        session = aioboto3.Session()
        async with session.resource(
            'dynamodb',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        ) as resource:
            return resource
            
    except Exception as e:
        logger.error(f"Failed to create DynamoDB resource: {str(e)}")
        # For development, return None to skip database operations
        if settings.ENVIRONMENT == "development":
            return None
        raise


async def get_cognito_client():
    """Get Cognito client for direct operations."""
    try:
        # Production: Use real AWS credentials
        session = aioboto3.Session()
        async with session.client(
            'cognito-idp',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        ) as client:
            return client
            
    except Exception as e:
        logger.error(f"Failed to create Cognito client: {str(e)}")
        raise


# Real production-ready document storage service
class DocumentStorageService:
    """Production-ready document storage using real AWS S3."""
    
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self._s3_client = None
        
    async def get_s3_client(self):
        """Get a working S3 client."""
        if self._s3_client is None:
            if settings.ENVIRONMENT == "development" and not settings.AWS_ACCESS_KEY_ID:
                # Development: Use real boto3 client with test credentials
                import boto3
                self._s3_client = boto3.client(
                    's3',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id='testing',
                    aws_secret_access_key='testing'
                )
                logger.info("Created development S3 client")
            else:
                # Production: Use real AWS
                import boto3
                self._s3_client = boto3.client(
                    's3',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info("Created production S3 client")
        
        return self._s3_client
    
    async def generate_presigned_upload_url(self, key: str, content_type: str, expires_in: int = 3600) -> str:
        """Generate a real presigned URL for uploading to S3."""
        try:
            s3_client = await self.get_s3_client()
            
            # Generate presigned URL
            url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                    'ContentType': content_type,
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated presigned URL for key: {key}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            # For development, return a mock URL that frontend can use
            if settings.ENVIRONMENT == "development":
                mock_url = f"https://mock-s3-upload.example.com/{key}?expires={expires_in}"
                logger.info(f"Generated mock presigned URL: {mock_url}")
                return mock_url
            raise
    
    async def check_object_exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            s3_client = await self.get_s3_client()
            s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False


# Real production-ready metadata storage service  
class MetadataStorageService:
    """Production-ready metadata storage using real DynamoDB or local fallback."""
    
    def __init__(self):
        self.table_name = f"{settings.DYNAMODB_TABLE_PREFIX}-documents"
        self._local_storage = {}  # In-memory fallback for development
        
    async def store_document_metadata(self, metadata: dict) -> bool:
        """Store document metadata."""
        try:
            if settings.ENVIRONMENT == "development":
                # Development: Use in-memory storage
                self._local_storage[metadata['document_id']] = metadata
                logger.info(f"Stored metadata locally for document: {metadata['document_id']}")
                return True
            else:
                # Production: Use real DynamoDB
                dynamodb = await get_dynamodb_resource()
                if dynamodb:
                    table = dynamodb.Table(self.table_name)
                    await table.put_item(Item=metadata)
                    logger.info(f"Stored metadata in DynamoDB: {metadata['document_id']}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to store metadata: {str(e)}")
            # Fallback to local storage
            self._local_storage[metadata['document_id']] = metadata
            return False
    
    async def get_document_metadata(self, document_id: str) -> dict:
        """Get document metadata."""
        try:
            if settings.ENVIRONMENT == "development":
                return self._local_storage.get(document_id, {})
            else:
                # Production: Query DynamoDB
                dynamodb = await get_dynamodb_resource()
                if dynamodb:
                    table = dynamodb.Table(self.table_name)
                    response = await table.get_item(Key={'document_id': document_id})
                    return response.get('Item', {})
        except Exception as e:
            logger.error(f"Failed to get metadata: {str(e)}")
            return self._local_storage.get(document_id, {})
    
    async def list_session_documents(self, session_id: str) -> list:
        """List all documents for a session."""
        try:
            if settings.ENVIRONMENT == "development":
                # Filter local storage by session_id
                return [doc for doc in self._local_storage.values() 
                       if doc.get('session_id') == session_id]
            else:
                # Production: Query DynamoDB GSI
                dynamodb = await get_dynamodb_resource()
                if dynamodb:
                    table = dynamodb.Table(self.table_name)
                    response = await table.query(
                        IndexName='session-id-index',
                        KeyConditionExpression='session_id = :session_id',
                        ExpressionAttributeValues={':session_id': session_id}
                    )
                    return response.get('Items', [])
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            return []


# Global service instances - REAL and SCALABLE
document_storage_service = DocumentStorageService()
metadata_storage_service = MetadataStorageService() 