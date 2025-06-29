import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
TABLE_ANSWERS = os.environ.get('TABLE_ANSWERS', 'visamate-ai-wizardanswers')


def lambda_handler(event, context):
    """Validate questionnaire answers for completeness and consistency."""
    try:
        logger.info(f"Validating answers for event: {json.dumps(event, default=str)}")
        
        user_id = event.get('user_id')
        session_id = event.get('session_id')
        
        if not user_id or not session_id:
            return {
                'statusCode': 400,
                'valid': False,
                'errors': ['Missing user_id or session_id']
            }
        
        # Get answers from DynamoDB
        answers = get_user_answers(user_id, session_id)
        
        # Validate answers
        validation_result = validate_questionnaire_answers(answers)
        
        return {
            'statusCode': 200,
            'valid': validation_result['valid'],
            'answers': answers,
            'validation_errors': validation_result.get('errors', []),
            'completeness_score': validation_result.get('completeness_score', 0),
            'validated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            'statusCode': 500,
            'valid': False,
            'error': str(e)
        }


def get_user_answers(user_id, session_id):
    """Get user answers from DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_ANSWERS)
        
        # Query answers for user
        response = table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id}
        )
        
        answers = {}
        for item in response.get('Items', []):
            answers[item['question_id']] = item.get('answer')
        
        logger.info(f"Retrieved {len(answers)} answers for user {user_id}")
        return answers
        
    except Exception as e:
        logger.error(f"Failed to get user answers: {str(e)}")
        return {}


def validate_questionnaire_answers(answers):
    """Validate questionnaire answers for completeness."""
    required_fields = [
        'passport_country_code',
        'current_residence',
        'date_of_birth',
        'institution_name',
        'program_name',
        'has_language_test',
        'has_gic',
        'tuition_paid'
    ]
    
    errors = []
    missing_fields = []
    
    for field in required_fields:
        if field not in answers or not answers[field]:
            missing_fields.append(field)
    
    if missing_fields:
        errors.append(f"Missing required fields: {', '.join(missing_fields)}")
    
    # Additional validation rules
    if 'date_of_birth' in answers:
        try:
            # Basic date validation
            datetime.fromisoformat(answers['date_of_birth'])
        except:
            errors.append("Invalid date of birth format")
    
    completeness_score = ((len(required_fields) - len(missing_fields)) / len(required_fields)) * 100
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'completeness_score': completeness_score,
        'missing_fields': missing_fields
    } 