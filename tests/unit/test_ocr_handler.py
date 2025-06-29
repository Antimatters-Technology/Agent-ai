import json
import pytest
import boto3
from moto import mock_textract, mock_s3, mock_sns, mock_dynamodb
from unittest.mock import patch, MagicMock
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from lambdas.ocr_handler import lambda_handler


@pytest.fixture
def sample_sqs_event():
    """Sample SQS event for testing."""
    return {
        'Records': [
            {
                'eventSource': 'aws:sqs',
                'body': json.dumps({
                    'document_id': 'test-doc-123',
                    'session_id': 'test-session-456',
                    'user_id': 'test-user-789',
                    'bucket': 'visamate-documents',
                    'key': 'raw/test-session-456/test-doc-123/passport.jpg',
                    'document_type': 'passport',
                    'file_name': 'passport.jpg',
                    'content_type': 'image/jpeg',
                    'file_size': 1024000,
                    'application_id': 'test-session-456',
                    'timestamp': '2024-01-15T10:00:00Z'
                })
            }
        ]
    }


@pytest.fixture
def sample_textract_response():
    """Sample Textract response for testing."""
    return {
        'Blocks': [
            {
                'BlockType': 'LINE',
                'Text': 'PASSPORT',
                'Confidence': 99.5,
                'Geometry': {
                    'BoundingBox': {
                        'Width': 0.2,
                        'Height': 0.05,
                        'Left': 0.1,
                        'Top': 0.1
                    }
                }
            },
            {
                'BlockType': 'LINE',
                'Text': 'Passport No: AB123456',
                'Confidence': 95.2,
                'Geometry': {
                    'BoundingBox': {
                        'Width': 0.3,
                        'Height': 0.04,
                        'Left': 0.1,
                        'Top': 0.2
                    }
                }
            },
            {
                'BlockType': 'LINE',
                'Text': 'CANADA',
                'Confidence': 98.1,
                'Geometry': {
                    'BoundingBox': {
                        'Width': 0.15,
                        'Height': 0.03,
                        'Left': 0.1,
                        'Top': 0.3
                    }
                }
            }
        ]
    }


class TestOCRHandler:
    """Test cases for OCR Handler Lambda function."""

    @mock_textract
    @mock_s3
    @mock_sns
    @mock_dynamodb
    def test_lambda_handler_success_jpg(self, sample_sqs_event, sample_textract_response):
        """Test successful OCR processing of JPG file."""
        
        # Set up environment variables
        os.environ.update({
            'BUCKET_JSON': 'visamate-documents/json',
            'SNS_OCR_TOPIC': 'arn:aws:sns:us-east-1:123456789012:ocr-complete-topic',
            'TABLE_DOCS': 'visamate-ai-documents',
            'AWS_REGION': 'us-east-1'
        })
        
        # Mock AWS services
        textract_client = boto3.client('textract', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='us-east-1')
        sns_client = boto3.client('sns', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create S3 bucket
        s3_client.create_bucket(Bucket='visamate-documents')
        
        # Create SNS topic
        topic_response = sns_client.create_topic(Name='ocr-complete-topic')
        
        # Create DynamoDB table
        table = dynamodb.create_table(
            TableName='visamate-ai-documents',
            KeySchema=[
                {'AttributeName': 'document_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'document_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Mock Textract response
        with patch('boto3.client') as mock_boto3:
            mock_textract = MagicMock()
            mock_textract.detect_document_text.return_value = sample_textract_response
            mock_boto3.return_value = mock_textract
            
            # Execute Lambda
            result = lambda_handler(sample_sqs_event, {})
            
            # Assertions
            assert result['statusCode'] == 200
            assert 'processed_documents' in result
            assert result['processed_documents'] == 1
            
            # Verify Textract was called
            mock_textract.detect_document_text.assert_called_once()

    @mock_textract
    @mock_s3
    @mock_sns
    @mock_dynamodb
    def test_lambda_handler_pdf_file(self, sample_sqs_event, sample_textract_response):
        """Test OCR processing of PDF file using analyze_document."""
        
        # Modify event for PDF
        pdf_event = sample_sqs_event.copy()
        body = json.loads(pdf_event['Records'][0]['body'])
        body.update({
            'file_name': 'transcript.pdf',
            'content_type': 'application/pdf',
            'key': 'raw/test-session-456/test-doc-123/transcript.pdf'
        })
        pdf_event['Records'][0]['body'] = json.dumps(body)
        
        # Set up environment
        os.environ.update({
            'BUCKET_JSON': 'visamate-documents/json',
            'SNS_OCR_TOPIC': 'arn:aws:sns:us-east-1:123456789012:ocr-complete-topic',
            'TABLE_DOCS': 'visamate-ai-documents',
            'AWS_REGION': 'us-east-1'
        })
        
        # Mock services
        textract_client = boto3.client('textract', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='us-east-1')
        sns_client = boto3.client('sns', region_name='us-east-1')
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create resources
        s3_client.create_bucket(Bucket='visamate-documents')
        sns_client.create_topic(Name='ocr-complete-topic')
        dynamodb.create_table(
            TableName='visamate-ai-documents',
            KeySchema=[{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'document_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Mock Textract for PDF
        with patch('boto3.client') as mock_boto3:
            mock_textract = MagicMock()
            mock_textract.analyze_document.return_value = sample_textract_response
            mock_boto3.return_value = mock_textract
            
            result = lambda_handler(pdf_event, {})
            
            assert result['statusCode'] == 200
            mock_textract.analyze_document.assert_called_once()

    def test_lambda_handler_file_too_large(self, sample_sqs_event):
        """Test handling of files that exceed size limit."""
        
        # Modify event for large file
        large_file_event = sample_sqs_event.copy()
        body = json.loads(large_file_event['Records'][0]['body'])
        body['file_size'] = 6 * 1024 * 1024  # 6MB - exceeds 5MB limit
        large_file_event['Records'][0]['body'] = json.dumps(body)
        
        os.environ.update({
            'BUCKET_JSON': 'visamate-documents/json',
            'SNS_OCR_TOPIC': 'arn:aws:sns:us-east-1:123456789012:ocr-complete-topic',
            'TABLE_DOCS': 'visamate-ai-documents',
            'AWS_REGION': 'us-east-1'
        })
        
        result = lambda_handler(large_file_event, {})
        
        # Should still return 200 but with errors
        assert result['statusCode'] == 200
        assert 'errors' in result
        assert len(result['errors']) > 0

    def test_lambda_handler_invalid_json(self):
        """Test handling of invalid JSON in SQS message."""
        
        invalid_event = {
            'Records': [
                {
                    'eventSource': 'aws:sqs',
                    'body': 'invalid json content'
                }
            ]
        }
        
        result = lambda_handler(invalid_event, {})
        
        assert result['statusCode'] == 200
        assert 'errors' in result

    @mock_textract
    def test_field_mapping_passport(self, sample_textract_response):
        """Test field mapping for passport documents."""
        
        # Import the mapping function
        from lambdas.ocr_handler import map_ocr_to_questionnaire_fields
        
        ocr_result = {
            'text_blocks': [
                {'text': 'PASSPORT', 'confidence': 99.5},
                {'text': 'Passport No: AB123456', 'confidence': 95.2},
                {'text': 'CANADA', 'confidence': 98.1}
            ]
        }
        
        mapped_data = map_ocr_to_questionnaire_fields(ocr_result, 'passport')
        
        assert mapped_data.get('has_passport') is True
        assert mapped_data.get('passport_number') == 'AB123456'
        assert mapped_data.get('nationality') == 'canada'

    @mock_textract
    def test_field_mapping_ielts(self):
        """Test field mapping for IELTS documents."""
        
        from lambdas.ocr_handler import map_ocr_to_questionnaire_fields
        
        ocr_result = {
            'text_blocks': [
                {'text': 'IELTS Test Report Form', 'confidence': 99.0},
                {'text': 'Overall Band Score: 7.5', 'confidence': 98.5},
                {'text': 'Listening: 8.0', 'confidence': 97.0},
                {'text': 'Reading: 7.0', 'confidence': 96.5}
            ]
        }
        
        mapped_data = map_ocr_to_questionnaire_fields(ocr_result, 'ielts_results')
        
        assert mapped_data.get('has_language_test') is True
        assert mapped_data.get('test_type') == 'IELTS'
        assert mapped_data.get('overall_score') == 7.5

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        
        from lambdas.ocr_handler import process_textract_blocks
        
        textract_response = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'Test 1', 'Confidence': 90.0},
                {'BlockType': 'LINE', 'Text': 'Test 2', 'Confidence': 95.0},
                {'BlockType': 'LINE', 'Text': 'Test 3', 'Confidence': 85.0}
            ]
        }
        
        result = process_textract_blocks(textract_response, 'sync_detect_text')
        
        assert result['average_confidence'] == 90.0  # (90+95+85)/3
        assert len(result['confidence_scores']) == 3
        assert result['line_blocks'] == 3

    @mock_dynamodb
    def test_update_document_status_success(self):
        """Test successful document status update."""
        
        from lambdas.ocr_handler import update_document_with_ocr_results
        
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='visamate-ai-documents',
            KeySchema=[{'AttributeName': 'document_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'document_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Insert test document
        table.put_item(Item={
            'document_id': 'test-doc-123',
            'status': 'processing'
        })
        
        ocr_result = {
            'mode': 'sync_detect_text',
            'text_blocks': [{'text': 'test'}],
            'average_confidence': 95.0
        }
        
        mapped_data = {'has_passport': True}
        
        os.environ['TABLE_DOCS'] = 'visamate-ai-documents'
        
        # Should not raise exception
        update_document_with_ocr_results('test-doc-123', ocr_result, mapped_data, 'json/test.json')

    @mock_sns
    def test_publish_completion_notification(self):
        """Test SNS notification publishing."""
        
        from lambdas.ocr_handler import publish_ocr_complete_notification
        
        # Create SNS topic
        sns_client = boto3.client('sns', region_name='us-east-1')
        topic_response = sns_client.create_topic(Name='ocr-complete-topic')
        topic_arn = topic_response['TopicArn']
        
        os.environ['SNS_OCR_TOPIC'] = topic_arn
        
        ocr_result = {
            'mode': 'sync_detect_text',
            'text_blocks': [{'text': 'test'}],
            'average_confidence': 95.0
        }
        
        mapped_data = {'has_passport': True}
        
        # Should not raise exception
        publish_ocr_complete_notification('test-doc-123', ocr_result, mapped_data)

    def test_empty_sqs_records(self):
        """Test handling of empty SQS records."""
        
        empty_event = {'Records': []}
        
        result = lambda_handler(empty_event, {})
        
        assert result['statusCode'] == 200
        assert result['processed_documents'] == 0

    def test_malformed_sqs_record(self):
        """Test handling of malformed SQS record."""
        
        malformed_event = {
            'Records': [
                {
                    'eventSource': 'aws:sqs',
                    'body': json.dumps({
                        'document_id': 'test-doc-123'
                        # Missing required fields
                    })
                }
            ]
        }
        
        result = lambda_handler(malformed_event, {})
        
        assert result['statusCode'] == 200
        assert 'errors' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 