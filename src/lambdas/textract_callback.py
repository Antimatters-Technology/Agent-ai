import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

textract_client = boto3.client('textract')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')

# Environment variables
BUCKET_JSON = os.environ.get('BUCKET_JSON', 'visamate-documents/json')
SNS_OCR_TOPIC = os.environ.get('SNS_OCR_TOPIC')
TABLE_DOCS = os.environ.get('TABLE_DOCS', 'visamate-ai-documents')


def lambda_handler(event, context):
    """Handle async Textract completion notifications."""
    try:
        logger.info(f"Received Textract callback: {json.dumps(event, default=str)}")
        
        # Parse SNS message
        for record in event.get('Records', []):
            if record.get('EventSource') == 'aws:sns':
                message = json.loads(record['Sns']['Message'])
                
                # Extract Textract job information
                job_id = message.get('JobId')
                job_status = message.get('Status')
                document_location = message.get('DocumentLocation', {})
                
                if job_status == 'SUCCEEDED':
                    result = process_textract_completion(job_id, document_location)
                    logger.info(f"Successfully processed Textract job {job_id}")
                    return result
                elif job_status == 'FAILED':
                    logger.error(f"Textract job {job_id} failed")
                    return handle_textract_failure(job_id, message)
                else:
                    logger.warning(f"Unknown Textract job status: {job_status}")
        
        return {'statusCode': 200, 'body': 'Processed'}
        
    except Exception as e:
        logger.error(f"Textract callback error: {str(e)}")
        return {'statusCode': 500, 'body': f'Error: {str(e)}'}


def process_textract_completion(job_id, document_location):
    """Process completed Textract job and extract results."""
    try:
        # Get Textract results
        textract_results = get_textract_results(job_id)
        
        # Extract document ID from S3 key
        s3_key = document_location.get('S3Object', {}).get('Name', '')
        document_id = extract_document_id_from_key(s3_key)
        
        # Process and save results
        ocr_result = process_textract_blocks(textract_results, job_id)
        json_key = save_ocr_results_to_s3(ocr_result, document_id)
        
        # Update document status
        update_document_with_ocr_results(document_id, ocr_result, json_key)
        
        # Map to questionnaire fields
        mapped_data = map_ocr_to_questionnaire_fields(ocr_result)
        
        # Publish completion notification
        publish_ocr_complete_notification(document_id, ocr_result, mapped_data)
        
        return {
            'statusCode': 200,
            'document_id': document_id,
            'job_id': job_id,
            'text_blocks_found': len(ocr_result.get('text_blocks', [])),
            'mapped_fields': len(mapped_data)
        }
        
    except Exception as e:
        logger.error(f"Error processing Textract completion: {str(e)}")
        raise


def get_textract_results(job_id):
    """Get paginated results from Textract async job."""
    all_blocks = []
    next_token = None
    
    while True:
        try:
            if next_token:
                response = textract_client.get_document_text_detection(
                    JobId=job_id,
                    NextToken=next_token
                )
            else:
                response = textract_client.get_document_text_detection(JobId=job_id)
            
            all_blocks.extend(response.get('Blocks', []))
            
            next_token = response.get('NextToken')
            if not next_token:
                break
                
        except Exception as e:
            logger.error(f"Error getting Textract results: {str(e)}")
            raise
    
    return {
        'Blocks': all_blocks,
        'JobStatus': 'SUCCEEDED',
        'JobId': job_id
    }


def process_textract_blocks(textract_results, job_id):
    """Process Textract blocks into structured format."""
    start_time = datetime.utcnow()
    
    text_blocks = []
    confidence_scores = []
    
    for block in textract_results.get('Blocks', []):
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
        'mode': 'async_detect_text',
        'job_id': job_id,
        'text_blocks': text_blocks,
        'confidence_scores': confidence_scores,
        'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
        'processing_time_ms': processing_time,
        'total_blocks': len(textract_results.get('Blocks', [])),
        'line_blocks': len(text_blocks)
    }


def map_ocr_to_questionnaire_fields(ocr_result):
    """Map OCR extracted text to questionnaire fields."""
    mapped_data = {}
    
    try:
        all_text = ' '.join([block.get('text', '').lower() for block in ocr_result.get('text_blocks', [])])
        
        # Basic field extraction (same as sync version)
        if 'passport' in all_text:
            mapped_data['has_passport'] = True
        if 'ielts' in all_text:
            mapped_data['has_language_test'] = True
            mapped_data['test_type'] = 'IELTS'
        
        # Extract passport number
        import re
        passport_match = re.search(r'passport\s*(?:no|number)?\s*:?\s*([A-Z0-9]{6,9})', all_text, re.IGNORECASE)
        if passport_match:
            mapped_data['passport_number'] = passport_match.group(1).upper()
        
        logger.info(f"Mapped {len(mapped_data)} fields from async OCR results")
        
    except Exception as e:
        logger.error(f"Field mapping error: {str(e)}")
    
    return mapped_data


def save_ocr_results_to_s3(ocr_result, document_id):
    """Save OCR results to S3 as JSON."""
    try:
        import uuid
        json_key = f"json/{document_id}_async_{uuid.uuid4().hex[:8]}.json"
        bucket_name = BUCKET_JSON.split('/')[0] if '/' in BUCKET_JSON else BUCKET_JSON
        
        ocr_result['document_id'] = document_id
        ocr_result['processed_at'] = datetime.utcnow().isoformat()
        ocr_result['processor_version'] = '1.0_async'
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=json_key,
            Body=json.dumps(ocr_result, default=str, indent=2),
            ContentType='application/json'
        )
        
        logger.info(f"Saved async OCR results to s3://{bucket_name}/{json_key}")
        return json_key
        
    except Exception as e:
        logger.error(f"Failed to save async OCR results to S3: {str(e)}")
        return ''


def update_document_with_ocr_results(document_id, ocr_result, json_key):
    """Update document with OCR results."""
    try:
        table = dynamodb.Table(TABLE_DOCS)
        
        table.update_item(
            Key={'document_id': document_id},
            UpdateExpression="SET #status = :status, ocr_results = :ocr_results, processed_at = :processed_at",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'processed',
                ':ocr_results': {
                    'mode': ocr_result.get('mode'),
                    'job_id': ocr_result.get('job_id'),
                    'text_blocks_count': len(ocr_result.get('text_blocks', [])),
                    'average_confidence': ocr_result.get('average_confidence', 0),
                    'json_s3_key': json_key,
                    'async_processing': True
                },
                ':processed_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Updated document {document_id} with async OCR results")
        
    except Exception as e:
        logger.error(f"Failed to update document with async OCR results: {str(e)}")


def publish_ocr_complete_notification(document_id, ocr_result, mapped_data):
    """Publish OCR completion notification to SNS."""
    try:
        if not SNS_OCR_TOPIC:
            logger.warning("SNS_OCR_TOPIC not configured, skipping notification")
            return
        
        message = {
            'event_type': 'ocr_complete_async',
            'document_id': document_id,
            'processing_mode': ocr_result.get('mode'),
            'job_id': ocr_result.get('job_id'),
            'text_blocks_found': len(ocr_result.get('text_blocks', [])),
            'average_confidence': ocr_result.get('average_confidence', 0),
            'mapped_fields_count': len(mapped_data),
            'mapped_fields': list(mapped_data.keys()),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        sns_client.publish(
            TopicArn=SNS_OCR_TOPIC,
            Message=json.dumps(message, default=str),
            Subject=f'Async OCR Processing Complete - Document {document_id}'
        )
        
        logger.info(f"Published async OCR complete notification for document {document_id}")
        
    except Exception as e:
        logger.error(f"Failed to publish async SNS notification: {str(e)}")


def handle_textract_failure(job_id, message):
    """Handle failed Textract job."""
    try:
        logger.error(f"Textract job {job_id} failed: {message}")
        
        # Could extract document_id and update status to failed
        # For now, just log the failure
        
        return {
            'statusCode': 200,
            'job_id': job_id,
            'status': 'failed',
            'message': 'Textract job failed'
        }
        
    except Exception as e:
        logger.error(f"Error handling Textract failure: {str(e)}")
        return {'statusCode': 500, 'error': str(e)}


def extract_document_id_from_key(object_key):
    """Extract document ID from S3 object key."""
    parts = object_key.split('/')
    if len(parts) >= 3:
        return parts[2]  # document_id from raw/{session_id}/{document_id}/{filename}
    else:
        filename = parts[-1]
        return filename.split('.')[0] if '.' in filename else filename 