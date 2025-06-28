"""
AWS Cognito authentication module for VisaMate AI platform.
Handles user authentication, JWT tokens, and Cognito integration.
"""

import boto3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from botocore.exceptions import ClientError

from src.core.config import settings


class CognitoAuth:
    """AWS Cognito authentication handler."""
    
    def __init__(self):
        self.client = boto3.client(
            'cognito-idp',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.client_id = settings.COGNITO_CLIENT_ID
        self.client_secret = settings.COGNITO_CLIENT_SECRET
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def register_user(self, username: str, password: str, email: str, 
                     phone_number: Optional[str] = None, **attributes) -> Dict[str, Any]:
        """Register a new user in Cognito User Pool."""
        try:
            user_attributes = [
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'}
            ]
            
            if phone_number:
                user_attributes.append({'Name': 'phone_number', 'Value': phone_number})
            
            # Add custom attributes
            for key, value in attributes.items():
                if key.startswith('custom:'):
                    user_attributes.append({'Name': key, 'Value': str(value)})
            
            response = self.client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=user_attributes,
                TemporaryPassword=password,
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            # Set permanent password
            self.client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=username,
                Password=password,
                Permanent=True
            )
            
            return {
                "user_id": response['User']['Username'],
                "status": "success",
                "message": "User registered successfully"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password does not meet requirements"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Registration failed: {str(e)}"
                )
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with Cognito."""
        try:
            response = self.client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            if 'AuthenticationResult' in response:
                tokens = response['AuthenticationResult']
                
                # Get user details
                user_response = self.client.admin_get_user(
                    UserPoolId=self.user_pool_id,
                    Username=username
                )
                
                user_attributes = {
                    attr['Name']: attr['Value'] 
                    for attr in user_response['UserAttributes']
                }
                
                return {
                    "access_token": tokens['AccessToken'],
                    "refresh_token": tokens.get('RefreshToken'),
                    "id_token": tokens.get('IdToken'),
                    "token_type": "bearer",
                    "expires_in": tokens['ExpiresIn'],
                    "user": {
                        "username": username,
                        "email": user_attributes.get('email'),
                        "phone_number": user_attributes.get('phone_number'),
                        "user_status": user_response['UserStatus']
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )
            elif error_code == 'UserNotConfirmedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account not confirmed"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Authentication failed: {str(e)}"
                )
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            response = self.client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            tokens = response['AuthenticationResult']
            return {
                "access_token": tokens['AccessToken'],
                "id_token": tokens.get('IdToken'),
                "token_type": "bearer",
                "expires_in": tokens['ExpiresIn']
            }
            
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token refresh failed"
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and extract user information."""
        try:
            # For production, you should verify with Cognito's public keys
            # This is a simplified version
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            username = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            return payload
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def get_user_by_token(self, access_token: str) -> Dict[str, Any]:
        """Get user information using access token."""
        try:
            response = self.client.get_user(AccessToken=access_token)
            
            user_attributes = {
                attr['Name']: attr['Value'] 
                for attr in response['UserAttributes']
            }
            
            return {
                "username": response['Username'],
                "email": user_attributes.get('email'),
                "phone_number": user_attributes.get('phone_number'),
                "attributes": user_attributes
            }
            
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token"
            )
    
    def logout_user(self, access_token: str) -> Dict[str, Any]:
        """Logout user by invalidating the access token."""
        try:
            self.client.global_sign_out(AccessToken=access_token)
            return {"message": "User logged out successfully"}
            
        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logout failed"
            )


# Global auth instance
cognito_auth = CognitoAuth() 