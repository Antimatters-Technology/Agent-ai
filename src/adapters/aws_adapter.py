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