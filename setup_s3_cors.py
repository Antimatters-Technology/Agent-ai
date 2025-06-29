"""
Configure CORS on S3 bucket to allow frontend uploads.
"""
import boto3
import json
from botocore.exceptions import ClientError

def setup_s3_cors():
    """Configure CORS on the visamate-documents S3 bucket."""
    
    # S3 client
    s3_client = boto3.client(
        's3',
        region_name='us-east-1',
        aws_access_key_id='AKIA3QHW5A4FGZJGDUK7',
        aws_secret_access_key='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'
    )
    
    bucket_name = 'visamate-documents'
    
    # CORS configuration that allows frontend uploads
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': [
                    '*'
                ],
                'AllowedMethods': [
                    'GET',
                    'PUT',
                    'POST',
                    'DELETE',
                    'HEAD'
                ],
                'AllowedOrigins': [
                    'http://localhost:3000',
                    'http://localhost:3001', 
                    'https://visamate.ai',
                    'https://*.visamate.ai'
                ],
                'ExposeHeaders': [
                    'ETag',
                    'x-amz-meta-custom-header'
                ],
                'MaxAgeSeconds': 3600
            }
        ]
    }
    
    try:
        # Set CORS configuration
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        print(f"✅ Successfully configured CORS for bucket: {bucket_name}")
        
        # Verify CORS configuration
        response = s3_client.get_bucket_cors(Bucket=bucket_name)
        print("📋 Current CORS configuration:")
        print(json.dumps(response['CORSRules'], indent=2))
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ Bucket {bucket_name} does not exist!")
        elif error_code == 'AccessDenied':
            print(f"❌ Access denied! Check your AWS credentials.")
        else:
            print(f"❌ Error configuring CORS: {e}")
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def verify_bucket_exists():
    """Check if the S3 bucket exists."""
    s3_client = boto3.client(
        's3',
        region_name='us-east-1',
        aws_access_key_id='AKIA3QHW5A4FGZJGDUK7',
        aws_secret_access_key='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'
    )
    
    bucket_name = 'visamate-documents'
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket {bucket_name} exists and is accessible")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"❌ Bucket {bucket_name} does not exist!")
        elif error_code == '403':
            print(f"❌ Access denied to bucket {bucket_name}")
        else:
            print(f"❌ Error checking bucket: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Setting up S3 CORS configuration...")
    print("=" * 50)
    
    # Check if bucket exists first
    if verify_bucket_exists():
        setup_s3_cors()
    else:
        print("\n💡 To create the bucket, run:")
        print("aws s3 mb s3://visamate-documents --region us-east-1") 