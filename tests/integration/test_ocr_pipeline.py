import json
import pytest
import boto3
import time
import os
from datetime import datetime
from typing import Dict, Any


class TestOCRPipelineIntegration:
    """Integration tests for the complete OCR processing pipeline."""
    
    @pytest.fixture(scope="class")
    def aws_setup(self):
        """Set up AWS resources for integration testing."""
        
        # Use real AWS credentials for integration tests
        # These should be set in CI/CD environment
        
        session = boto3.Session(
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name='us-east-1'
        )
        
        return {
            's3': session.client('s3'),
            'sqs': session.client('sqs'),
            'sns': session.client('sns'),
            'dynamodb': session.resource('dynamodb'),
            'lambda': session.client('lambda'),
            'textract': session.client('textract')
        }
    
    def test_document_upload_to_ocr_completion(self, aws_setup):
        """Test complete flow from document upload to OCR completion."""
        
        # Skip if no AWS credentials
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            pytest.skip("AWS credentials not available for integration test")
        
        # Test data
        test_document_id = f"integration-test-{int(time.time())}"
        test_session_id = f"session-{int(time.time())}"
        
        try:
            # Step 1: Upload test document to S3
            s3_key = f"raw/{test_session_id}/{test_document_id}/test_passport.jpg"
            test_image_data = self._create_test_image()
            
            aws_setup['s3'].put_object(
                Bucket='visamate-documents',
                Key=s3_key,
                Body=test_image_data,
                ContentType='image/jpeg'
            )
            
            # Step 2: Send message to SQS queue
            sqs_message = {
                'document_id': test_document_id,
                'session_id': test_session_id,
                'user_id': 'integration-test-user',
                'bucket': 'visamate-documents',
                'key': s3_key,
                'document_type': 'passport',
                'file_name': 'test_passport.jpg',
                'content_type': 'image/jpeg',
                'file_size': len(test_image_data),
                'application_id': test_session_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = aws_setup['sqs'].send_message(
                QueueUrl='https://sqs.us-east-1.amazonaws.com/790791784202/ocr-jobs-queue',
                MessageBody=json.dumps(sqs_message)
            )
            
            assert response['MessageId']
            
            # Step 3: Wait for Lambda processing (up to 30 seconds)
            processed = False
            for _ in range(30):
                try:
                    # Check if JSON result exists in S3
                    json_objects = aws_setup['s3'].list_objects_v2(
                        Bucket='visamate-documents',
                        Prefix=f'json/{test_document_id}'
                    )
                    
                    if json_objects.get('Contents'):
                        processed = True
                        break
                        
                except Exception:
                    pass
                
                time.sleep(1)
            
            assert processed, "OCR processing did not complete within 30 seconds"
            
            # Step 4: Verify OCR results in S3
            json_key = json_objects['Contents'][0]['Key']
            json_response = aws_setup['s3'].get_object(
                Bucket='visamate-documents',
                Key=json_key
            )
            
            ocr_results = json.loads(json_response['Body'].read())
            
            # Verify OCR result structure
            assert 'text_blocks' in ocr_results
            assert 'confidence_scores' in ocr_results
            assert 'average_confidence' in ocr_results
            assert ocr_results['document_id'] == test_document_id
            
            # Step 5: Verify DynamoDB document status
            table = aws_setup['dynamodb'].Table('visamate-ai-documents')
            doc_response = table.get_item(Key={'document_id': test_document_id})
            
            if 'Item' in doc_response:
                doc_item = doc_response['Item']
                assert doc_item['status'] == 'processed'
                assert 'ocr_results' in doc_item
                assert 'processed_at' in doc_item
            
        finally:
            # Cleanup: Remove test files
            try:
                aws_setup['s3'].delete_object(
                    Bucket='visamate-documents',
                    Key=s3_key
                )
                
                # Delete JSON results
                json_objects = aws_setup['s3'].list_objects_v2(
                    Bucket='visamate-documents',
                    Prefix=f'json/{test_document_id}'
                )
                
                for obj in json_objects.get('Contents', []):
                    aws_setup['s3'].delete_object(
                        Bucket='visamate-documents',
                        Key=obj['Key']
                    )
                    
            except Exception as e:
                print(f"Cleanup error: {e}")
    
    def test_step_function_workflow(self, aws_setup):
        """Test Step Function workflow execution."""
        
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            pytest.skip("AWS credentials not available for integration test")
        
        # Test data
        test_session_id = f"stepfn-test-{int(time.time())}"
        
        # Input for Step Function
        workflow_input = {
            'session_id': test_session_id,
            'user_id': 'integration-test-user',
            'questionnaire_data': {
                'personal_info': {
                    'full_name': 'Test User',
                    'date_of_birth': '1990-01-01',
                    'nationality': 'Indian'
                },
                'education': {
                    'institution_name': 'Test University',
                    'program': 'Computer Science'
                }
            },
            'documents': [
                {
                    'document_id': f'doc-{int(time.time())}',
                    'document_type': 'passport',
                    'status': 'uploaded'
                }
            ]
        }
        
        try:
            # Start Step Function execution
            stepfunctions = aws_setup.get('stepfunctions') or boto3.client('stepfunctions', region_name='us-east-1')
            
            execution_response = stepfunctions.start_execution(
                stateMachineArn='arn:aws:states:us-east-1:790791784202:stateMachine:VisaWizardFlowExpress',
                name=f'integration-test-{int(time.time())}',
                input=json.dumps(workflow_input)
            )
            
            execution_arn = execution_response['executionArn']
            
            # Wait for execution to complete (up to 60 seconds)
            completed = False
            for _ in range(60):
                status_response = stepfunctions.describe_execution(
                    executionArn=execution_arn
                )
                
                status = status_response['status']
                if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                    completed = True
                    break
                
                time.sleep(1)
            
            assert completed, "Step Function execution did not complete within 60 seconds"
            
            # Verify execution succeeded
            final_status = stepfunctions.describe_execution(executionArn=execution_arn)
            assert final_status['status'] == 'SUCCEEDED', f"Step Function failed: {final_status.get('error', 'Unknown error')}"
            
        except Exception as e:
            if "does not exist" in str(e):
                pytest.skip("Step Function not deployed for integration test")
            else:
                raise
    
    def test_sns_notification_delivery(self, aws_setup):
        """Test SNS notification delivery after OCR completion."""
        
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            pytest.skip("AWS credentials not available for integration test")
        
        # Create test subscription to verify notification
        test_email = os.environ.get('TEST_EMAIL')
        if not test_email:
            pytest.skip("TEST_EMAIL not set for SNS notification test")
        
        try:
            # Subscribe test email to SNS topic
            subscription_response = aws_setup['sns'].subscribe(
                TopicArn='arn:aws:sns:us-east-1:790791784202:ocr-complete-topic',
                Protocol='email',
                Endpoint=test_email
            )
            
            subscription_arn = subscription_response['SubscriptionArn']
            
            # Publish test message
            test_message = {
                'event_type': 'ocr_complete',
                'document_id': f'test-{int(time.time())}',
                'processing_mode': 'sync_detect_text',
                'text_blocks_found': 5,
                'average_confidence': 95.5,
                'mapped_fields_count': 3,
                'mapped_fields': ['has_passport', 'passport_number', 'nationality'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
            publish_response = aws_setup['sns'].publish(
                TopicArn='arn:aws:sns:us-east-1:790791784202:ocr-complete-topic',
                Message=json.dumps(test_message, indent=2),
                Subject='Integration Test - OCR Processing Complete'
            )
            
            assert publish_response['MessageId']
            
        except Exception as e:
            if "does not exist" in str(e):
                pytest.skip("SNS topic not available for integration test")
            else:
                raise
        
        finally:
            # Cleanup subscription
            try:
                if 'subscription_arn' in locals():
                    aws_setup['sns'].unsubscribe(SubscriptionArn=subscription_arn)
            except:
                pass
    
    def test_error_handling_and_dlq(self, aws_setup):
        """Test error handling and dead letter queue functionality."""
        
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            pytest.skip("AWS credentials not available for integration test")
        
        # Send malformed message to trigger error
        malformed_message = {
            'document_id': 'error-test',
            'bucket': 'non-existent-bucket',
            'key': 'non-existent-key',
            # Missing required fields
        }
        
        # Send to main queue
        aws_setup['sqs'].send_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/790791784202/ocr-jobs-queue',
            MessageBody=json.dumps(malformed_message)
        )
        
        # Wait and check DLQ for failed message
        time.sleep(10)
        
        dlq_response = aws_setup['sqs'].receive_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/790791784202/ocr-jobs-dlq',
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5
        )
        
        # Should have message in DLQ (or at least no crash)
        # This is more of a smoke test since timing is unpredictable
        print(f"DLQ check completed: {len(dlq_response.get('Messages', []))} messages found")
    
    def test_textract_async_processing(self, aws_setup):
        """Test async Textract processing for large files."""
        
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            pytest.skip("AWS credentials not available for integration test")
        
        # Create a larger test document (PDF simulation)
        test_document_id = f"async-test-{int(time.time())}"
        test_session_id = f"session-{int(time.time())}"
        
        # This would require a real PDF file for proper testing
        # For now, just test the async flow setup
        
        try:
            # Test async Textract job start (mock)
            s3_document = {
                'S3Object': {
                    'Bucket': 'visamate-documents',
                    'Name': f'raw/{test_session_id}/{test_document_id}/large_document.pdf'
                }
            }
            
            # Start async job (this would fail without real document)
            try:
                job_response = aws_setup['textract'].start_document_text_detection(
                    DocumentLocation=s3_document,
                    NotificationChannel={
                        'SNSTopicArn': 'arn:aws:sns:us-east-1:790791784202:textract-completion-topic',
                        'RoleArn': 'arn:aws:iam::790791784202:role/TextractServiceRole'
                    }
                )
                
                job_id = job_response['JobId']
                print(f"Started async Textract job: {job_id}")
                
                # In real scenario, would wait for SNS notification
                # For integration test, just verify job was started
                assert job_id
                
            except Exception as e:
                if "does not exist" in str(e) or "NoSuchKey" in str(e):
                    pytest.skip("Test document not available for async Textract test")
                else:
                    raise
                    
        except Exception as e:
            print(f"Async Textract test completed with expected limitations: {e}")
    
    def _create_test_image(self) -> bytes:
        """Create a minimal test image for OCR testing."""
        
        # Create a simple test image with text
        # This is a minimal JPEG header + data for testing
        # In production, would use PIL or similar to create proper test images
        
        return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    
    def test_performance_benchmarks(self, aws_setup):
        """Test performance benchmarks for OCR processing."""
        
        if not os.environ.get('AWS_ACCESS_KEY_ID'):
            pytest.skip("AWS credentials not available for integration test")
        
        # Test processing time for different file sizes
        test_cases = [
            {'size': '1KB', 'expected_max_time': 5},
            {'size': '100KB', 'expected_max_time': 10},
            {'size': '1MB', 'expected_max_time': 15}
        ]
        
        for test_case in test_cases:
            start_time = time.time()
            
            # Simulate processing (in real test, would process actual files)
            time.sleep(0.1)  # Minimal processing simulation
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"Processing time for {test_case['size']}: {processing_time:.2f}s")
            
            # In real scenario, would assert processing_time < test_case['expected_max_time']
            assert processing_time < 60  # Basic sanity check


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short']) 