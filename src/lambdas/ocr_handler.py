"""
AWS Lambda function for OCR processing using Amazon Textract.
Handles document text extraction and publishes results to SNS topic.
"""

import json
import boto3
import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import base64

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

# Environment variables
BUCKET_RAW = os.environ.get('BUCKET_RAW', 'visamate-documents/raw')
BUCKET_JSON = os.environ.get('BUCKET_JSON', 'visamate-documents/json')
SNS_OCR_TOPIC = os.environ.get('SNS_OCR_TOPIC')
TABLE_DOCS = os.environ.get('TABLE_DOCS', 'visamate-ai-documents')
TABLE_ANSWERS = os.environ.get('TABLE_ANSWERS', 'visamate-ai-wizardanswers')

# Constants
MAX_FILE_SIZE_MB = 5
MAX_PAGES_SYNC = 5
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.tiff', '.tif']
SUPPORTED_DOC_FORMATS = ['.pdf']


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for OCR processing.
    
    Args:
        event: SQS event containing S3 object information
        context: Lambda runtime context
        
    Returns:
        Processing result dictionary
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Process each SQS record
        results = []
        for record in event.get('Records', []):
            try:
                result = process_sqs_record(record)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process record: {str(e)}")
                results.append({
                    'status': 'error',
                    'error': str(e),
                    'record_id': record.get('messageId', 'unknown')
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(results)} records',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


def process_sqs_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single SQS record containing S3 event notification.
    
    Args:
        record: SQS record with S3 event data
        
    Returns:
        Processing result
    """
    try:
        # Parse S3 event from SQS message
        message_body = json.loads(record['body'])
        
        # Handle S3 event notification format
        if 'Records' in message_body:
            s3_record = message_body['Records'][0]
            bucket_name = s3_record['s3']['bucket']['name']
            object_key = s3_record['s3']['object']['key']
        else:
            # Direct SQS message format
            bucket_name = message_body.get('bucket', 'visamate-documents')
            object_key = message_body.get('key', '')
        
        logger.info(f"Processing S3 object: s3://{bucket_name}/{object_key}")
        
        # Extract document metadata
        document_id = extract_document_id_from_key(object_key)
        file_extension = get_file_extension(object_key)
        
        # Get file size
        try:
            head_response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            file_size_mb = head_response['ContentLength'] / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Could not get file size: {str(e)}")
            file_size_mb = 0
        
        # Validate file
        if not is_supported_format(file_extension):
            raise ValueError(f"Unsupported file format: {file_extension}")
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise ValueError(f"File too large: {file_size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)")
        
        # Update document status to processing
        update_document_status(document_id, 'processing', {
            'processing_started_at': datetime.utcnow().isoformat(),
            'file_size_mb': file_size_mb,
            'file_extension': file_extension
        })
        
        # Process based on file type and size
        ocr_result = process_document_ocr(bucket_name, object_key, file_extension, file_size_mb)
        
        # Save OCR results to S3
        json_key = save_ocr_results_to_s3(ocr_result, document_id)
        
        # Update document with OCR results
        update_document_with_ocr_results(document_id, ocr_result, json_key)
        
        # Map OCR results to questionnaire fields
        mapped_data = map_ocr_to_questionnaire_fields(ocr_result)
        
        # Update wizard answers if mapping found data
        if mapped_data:
            update_wizard_answers(document_id, mapped_data)
        
        # Publish completion notification
        publish_ocr_complete_notification(document_id, ocr_result, mapped_data)
        
        return {
            'status': 'success',
            'document_id': document_id,
            'ocr_mode': ocr_result.get('mode', 'unknown'),
            'text_blocks_found': len(ocr_result.get('text_blocks', [])),
            'mapped_fields': len(mapped_data),
            'json_key': json_key
        }
        
    except Exception as e:
        logger.error(f"Error processing SQS record: {str(e)}")
        
        # Try to update document status to failed
        try:
            if 'document_id' in locals():
                update_document_status(document_id, 'failed', {
                    'error': str(e),
                    'failed_at': datetime.utcnow().isoformat()
                })
        except:
            pass
        
        raise


def process_document_ocr(bucket_name: str, object_key: str, file_extension: str, file_size_mb: float) -> Dict[str, Any]:
    """
    Process document using appropriate Textract method.
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key
        file_extension: File extension
        file_size_mb: File size in MB
        
    Returns:
        OCR results dictionary
    """
    try:
        # Determine processing mode
        if file_extension.lower() in SUPPORTED_IMAGE_FORMATS and file_size_mb < MAX_FILE_SIZE_MB:
            mode = 'sync_detect_text'
            return process_sync_detect_text(bucket_name, object_key)
        elif file_extension.lower() == '.pdf' and file_size_mb < MAX_FILE_SIZE_MB:
            mode = 'sync_analyze_document'
            return process_sync_analyze_document(bucket_name, object_key)
        else:
            mode = 'async_detect_text'
            return process_async_detect_text(bucket_name, object_key)
            
    except Exception as e:
        logger.error(f"OCR processing error: {str(e)}")
        return {
            'mode': 'error',
            'error': str(e),
            'text_blocks': [],
            'confidence_scores': [],
            'processing_time_ms': 0
        }


def process_sync_detect_text(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """Process image using synchronous text detection."""
    start_time = datetime.utcnow()
    
    try:
        response = textract_client.detect_document_text(
            Document={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': object_key
                }
            }
        )
        
        text_blocks = []
        confidence_scores = []
        
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_blocks.append({
                    'text': block.get('Text', ''),
                    'confidence': block.get('Confidence', 0),
                    'geometry': block.get('Geometry', {}),
                    'type': 'LINE'
                })
                confidence_scores.append(block.get('Confidence', 0))
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'mode': 'sync_detect_text',
            'text_blocks': text_blocks,
            'confidence_scores': confidence_scores,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'processing_time_ms': processing_time,
            'textract_response_id': response.get('ResponseMetadata', {}).get('RequestId')
        }
        
    except Exception as e:
        logger.error(f"Sync detect text error: {str(e)}")
        raise


def process_sync_analyze_document(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """Process PDF using synchronous document analysis."""
    start_time = datetime.utcnow()
    
    try:
        response = textract_client.analyze_document(
            Document={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': object_key
                }
            },
            FeatureTypes=['FORMS', 'TABLES']
        )
        
        text_blocks = []
        confidence_scores = []
        form_data = {}
        
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_blocks.append({
                    'text': block.get('Text', ''),
                    'confidence': block.get('Confidence', 0),
                    'geometry': block.get('Geometry', {}),
                    'type': 'LINE'
                })
                confidence_scores.append(block.get('Confidence', 0))
            elif block['BlockType'] == 'KEY_VALUE_SET':
                # Extract form key-value pairs
                if block.get('EntityTypes') and 'KEY' in block['EntityTypes']:
                    key_text = extract_text_from_relationships(block, response['Blocks'])
                    value_text = extract_value_from_key_block(block, response['Blocks'])
                    if key_text and value_text:
                        form_data[key_text] = value_text
        
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            'mode': 'sync_analyze_document',
            'text_blocks': text_blocks,
            'form_data': form_data,
            'confidence_scores': confidence_scores,
            'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            'processing_time_ms': processing_time,
            'textract_response_id': response.get('ResponseMetadata', {}).get('RequestId')
        }
        
    except Exception as e:
        logger.error(f"Sync analyze document error: {str(e)}")
        raise


def process_async_detect_text(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """Start asynchronous text detection for large documents."""
    try:
        response = textract_client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket_name,
                    'Name': object_key
                }
            },
            NotificationChannel={
                'SNSTopicArn': SNS_OCR_TOPIC,
                'RoleArn': 'arn:aws:iam::790791784202:role/TextractServiceRole'  # This would need to be created
            }
        )
        
        job_id = response['JobId']
        
        return {
            'mode': 'async_detect_text',
            'job_id': job_id,
            'status': 'IN_PROGRESS',
            'text_blocks': [],
            'confidence_scores': [],
            'processing_time_ms': 0,
            'message': 'Async processing started, results will be delivered via SNS'
        }
        
    except Exception as e:
        logger.error(f"Async detect text error: {str(e)}")
        # Fall back to sync processing for smaller files
        return process_sync_detect_text(bucket_name, object_key)


def extract_text_from_relationships(block: Dict[str, Any], all_blocks: List[Dict[str, Any]]) -> str:
    """Extract text from block relationships."""
    text_parts = []
    
    for relationship in block.get('Relationships', []):
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                child_block = next((b for b in all_blocks if b['Id'] == child_id), None)
                if child_block and child_block['BlockType'] == 'WORD':
                    text_parts.append(child_block.get('Text', ''))
    
    return ' '.join(text_parts)


def extract_value_from_key_block(key_block: Dict[str, Any], all_blocks: List[Dict[str, Any]]) -> str:
    """Extract value text from key block relationships."""
    for relationship in key_block.get('Relationships', []):
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                value_block = next((b for b in all_blocks if b['Id'] == value_id), None)
                if value_block:
                    return extract_text_from_relationships(value_block, all_blocks)
    return ''


def map_ocr_to_questionnaire_fields(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map OCR extracted text to questionnaire fields.
    
    Args:
        ocr_result: OCR processing results
        
    Returns:
        Mapped questionnaire fields
    """
    mapped_data = {}
    
    try:
        # Get all text content
        all_text = []
        for block in ocr_result.get('text_blocks', []):
            all_text.append(block.get('text', '').lower())
        
        full_text = ' '.join(all_text).lower()
        
        # Get form data if available
        form_data = ocr_result.get('form_data', {})
        
        # Field mapping rules (this would be expanded based on document types)
        field_mappings = {
            'passport_number': extract_passport_number(full_text, form_data),
            'full_name': extract_full_name(full_text, form_data),
            'date_of_birth': extract_date_of_birth(full_text, form_data),
            'nationality': extract_nationality(full_text, form_data),
            'ielts_scores': extract_ielts_scores(full_text, form_data),
            'institution_name': extract_institution_name(full_text, form_data),
            'program_name': extract_program_name(full_text, form_data),
            'gic_amount': extract_gic_amount(full_text, form_data),
            'tuition_amount': extract_tuition_amount(full_text, form_data)
        }
        
        # Only include fields that were successfully extracted
        for field, value in field_mappings.items():
            if value:
                mapped_data[field] = value
        
        logger.info(f"Mapped {len(mapped_data)} fields from OCR results")
        
    except Exception as e:
        logger.error(f"Field mapping error: {str(e)}")
    
    return mapped_data


def extract_passport_number(text: str, form_data: Dict[str, Any]) -> Optional[str]:
    """Extract passport number from text."""
    import re
    
    # Look in form data first
    for key, value in form_data.items():
        if 'passport' in key.lower() and 'number' in key.lower():
            return value
    
    # Pattern matching for common passport number formats
    patterns = [
        r'passport\s*(?:no|number|#)?\s*:?\s*([A-Z0-9]{6,9})',
        r'passport\s*([A-Z0-9]{6,9})',
        r'([A-Z]{1,2}[0-9]{6,8})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    return None


def extract_full_name(text: str, form_data: Dict[str, Any]) -> Optional[str]:
    """Extract full name from text."""
    # Look in form data first
    for key, value in form_data.items():
        if any(word in key.lower() for word in ['name', 'applicant', 'student']):
            if len(value.split()) >= 2:  # At least first and last name
                return value.title()
    
    # Pattern matching for names
    import re
    patterns = [
        r'name\s*:?\s*([A-Za-z\s]{2,50})',
        r'applicant\s*:?\s*([A-Za-z\s]{2,50})',
        r'student\s*:?\s*([A-Za-z\s]{2,50})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip().title()
            if len(name.split()) >= 2:
                return name
    
    return None


def extract_date_of_birth(text: str, form_data: Dict[str, Any]) -> Optional[str]:
    """Extract date of birth from text."""
    import re
    
    # Look in form data first
    for key, value in form_data.items():
        if 'birth' in key.lower() or 'dob' in key.lower():
            return value
    
    # Pattern matching for dates
    date_patterns = [
        r'(?:date\s*of\s*birth|dob|birth\s*date)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(?:born|birth)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def extract_nationality(text: str, form_data: Dict[str, Any]) -> Optional[str]:
    """Extract nationality from text."""
    # Look in form data first
    for key, value in form_data.items():
        if 'nationality' in key.lower() or 'country' in key.lower():
            return value
    
    # Common nationality patterns
    import re
    countries = ['indian', 'chinese', 'canadian', 'american', 'british', 'australian', 'german', 'french']
    
    for country in countries:
        if country in text.lower():
            return country.title()
    
    return None


def extract_ielts_scores(text: str, form_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """Extract IELTS scores from text."""
    import re
    
    scores = {}
    
    # Pattern for IELTS scores
    score_patterns = [
        r'listening\s*:?\s*(\d+\.?\d*)',
        r'reading\s*:?\s*(\d+\.?\d*)',
        r'writing\s*:?\s*(\d+\.?\d*)',
        r'speaking\s*:?\s*(\d+\.?\d*)',
        r'overall\s*:?\s*(\d+\.?\d*)'
    ]
    
    for i, pattern in enumerate(score_patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score_names = ['listening', 'reading', 'writing', 'speaking', 'overall']
            scores[score_names[i]] = float(match.group(1))
    
    return scores if scores else None


def extract_institution_name(text: str, form_data: Dict[str, Any]) -> Optional[str]:
    """Extract institution name from text."""
    # Look in form data first
    for key, value in form_data.items():
        if any(word in key.lower() for word in ['institution', 'university', 'college', 'school']):
            return value
    
    # Pattern matching for institutions
    import re
    patterns = [
        r'(?:university|college|institute|school)\s*(?:of|at)?\s*([A-Za-z\s]{2,50})',
        r'([A-Za-z\s]{2,50})\s*(?:university|college|institute)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    
    return None


def extract_program_name(text: str, form_data: Dict[str, Any]) -> Optional[str]:
    """Extract program name from text."""
    # Look in form data first
    for key, value in form_data.items():
        if any(word in key.lower() for word in ['program', 'course', 'degree', 'major']):
            return value
    
    return None


def extract_gic_amount(text: str, form_data: Dict[str, Any]) -> Optional[float]:
    """Extract GIC amount from text."""
    import re
    
    # Look for GIC amounts
    patterns = [
        r'gic\s*(?:amount)?\s*:?\s*(?:cad|can\$|\$)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'guaranteed\s*investment\s*certificate\s*:?\s*(?:cad|can\$|\$)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            return float(amount_str)
    
    return None


def extract_tuition_amount(text: str, form_data: Dict[str, Any]) -> Optional[float]:
    """Extract tuition amount from text."""
    import re
    
    # Look for tuition amounts
    patterns = [
        r'tuition\s*(?:fee|fees)?\s*:?\s*(?:cad|can\$|\$)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'program\s*fee\s*:?\s*(?:cad|can\$|\$)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            return float(amount_str)
    
    return None


def save_ocr_results_to_s3(ocr_result: Dict[str, Any], document_id: str) -> str:
    """Save OCR results to S3 as JSON."""
    try:
        json_key = f"json/{document_id}_{uuid.uuid4().hex[:8]}.json"
        bucket_name = BUCKET_JSON.split('/')[0] if '/' in BUCKET_JSON else BUCKET_JSON
        
        # Add metadata
        ocr_result['document_id'] = document_id
        ocr_result['processed_at'] = datetime.utcnow().isoformat()
        ocr_result['processor_version'] = '1.0'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=json_key,
            Body=json.dumps(ocr_result, default=str, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Saved OCR results to s3://{bucket_name}/{json_key}")
        return json_key
        
    except Exception as e:
        logger.error(f"Failed to save OCR results to S3: {str(e)}")
        return ''


def update_document_status(document_id: str, status: str, additional_data: Dict[str, Any] = None) -> None:
    """Update document status in DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_DOCS)
        
        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_attribute_names = {'#status': 'status'}
        expression_attribute_values = {
            ':status': status,
            ':updated_at': datetime.utcnow().isoformat()
        }
        
        if additional_data:
            for key, value in additional_data.items():
                update_expression += f", {key} = :{key}"
                expression_attribute_values[f":{key}"] = value
        
        table.update_item(
            Key={'document_id': document_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        logger.info(f"Updated document {document_id} status to {status}")
        
    except Exception as e:
        logger.error(f"Failed to update document status: {str(e)}")


def update_document_with_ocr_results(document_id: str, ocr_result: Dict[str, Any], json_key: str) -> None:
    """Update document with OCR results."""
    try:
        update_document_status(document_id, 'processed', {
            'ocr_results': {
                'mode': ocr_result.get('mode'),
                'text_blocks_count': len(ocr_result.get('text_blocks', [])),
                'average_confidence': ocr_result.get('average_confidence', 0),
                'processing_time_ms': ocr_result.get('processing_time_ms', 0),
                'json_s3_key': json_key
            },
            'processed_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to update document with OCR results: {str(e)}")


def update_wizard_answers(document_id: str, mapped_data: Dict[str, Any]) -> None:
    """Update wizard answers with mapped OCR data."""
    try:
        # This would need to be implemented based on your wizard answers table structure
        # For now, just log the mapped data
        logger.info(f"Would update wizard answers for document {document_id} with: {mapped_data}")
        
        # Example implementation (adjust based on your table structure):
        # table = dynamodb.Table(TABLE_ANSWERS)
        # for field, value in mapped_data.items():
        #     table.put_item(Item={
        #         'user_id': 'extracted_from_document_metadata',
        #         'question_id': field,
        #         'answer': value,
        #         'source': 'ocr_extraction',
        #         'document_id': document_id,
        #         'updated_at': datetime.utcnow().isoformat()
        #     })
        
    except Exception as e:
        logger.error(f"Failed to update wizard answers: {str(e)}")


def publish_ocr_complete_notification(document_id: str, ocr_result: Dict[str, Any], mapped_data: Dict[str, Any]) -> None:
    """Publish OCR completion notification to SNS."""
    try:
        if not SNS_OCR_TOPIC:
            logger.warning("SNS_OCR_TOPIC not configured, skipping notification")
            return
        
        message = {
            'event_type': 'ocr_complete',
            'document_id': document_id,
            'processing_mode': ocr_result.get('mode'),
            'text_blocks_found': len(ocr_result.get('text_blocks', [])),
            'average_confidence': ocr_result.get('average_confidence', 0),
            'mapped_fields_count': len(mapped_data),
            'mapped_fields': list(mapped_data.keys()),
            'processing_time_ms': ocr_result.get('processing_time_ms', 0),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns_client.publish(
            TopicArn=SNS_OCR_TOPIC,
            Message=json.dumps(message, default=str),
            Subject=f'OCR Processing Complete - Document {document_id}'
        )
        
        logger.info(f"Published OCR complete notification for document {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish SNS notification: {str(e)}")


def extract_document_id_from_key(object_key: str) -> str:
    """Extract document ID from S3 object key."""
    # Assuming key format: raw/{session_id}/{document_id}/{filename}
    parts = object_key.split('/')
    if len(parts) >= 3:
        return parts[2]  # document_id
    else:
        # Fallback: generate from filename
        filename = parts[-1]
        return filename.split('.')[0] if '.' in filename else filename


def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return '.' + filename.split('.')[-1].lower() if '.' in filename else ''


def is_supported_format(file_extension: str) -> bool:
    """Check if file format is supported."""
    return file_extension.lower() in SUPPORTED_IMAGE_FORMATS + SUPPORTED_DOC_FORMATS 