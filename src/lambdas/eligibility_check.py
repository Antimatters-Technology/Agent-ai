import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
TABLE_ANSWERS = os.environ.get('TABLE_ANSWERS', 'visamate-ai-wizardanswers')
TABLE_USERS = os.environ.get('TABLE_USERS', 'visamate-ai-users')


def lambda_handler(event, context):
    """Check visa eligibility based on answers and OCR data."""
    try:
        logger.info(f"Checking eligibility for event: {json.dumps(event, default=str)}")
        
        user_id = event.get('user_id')
        session_id = event.get('session_id')
        answers = event.get('answers', {})
        ocr_data = event.get('ocr_data', {})
        
        # Perform eligibility check
        eligibility_result = check_study_permit_eligibility(answers, ocr_data)
        
        return {
            'statusCode': 200,
            'eligible': eligibility_result['eligible'],
            'eligibility_score': eligibility_result['score'],
            'requirements_met': eligibility_result['requirements_met'],
            'requirements_missing': eligibility_result['requirements_missing'],
            'recommendations': eligibility_result['recommendations'],
            'checked_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Eligibility check error: {str(e)}")
        return {
            'statusCode': 500,
            'eligible': False,
            'error': str(e)
        }


def check_study_permit_eligibility(answers, ocr_data):
    """Check study permit eligibility based on requirements."""
    requirements = {
        'acceptance_letter': False,
        'financial_proof': False,
        'language_test': False,
        'medical_exam': False,
        'clean_criminal_record': False,
        'valid_passport': False,
        'provincial_attestation': False
    }
    
    score = 0
    max_score = len(requirements)
    
    # Check acceptance letter
    if answers.get('accepted_to_dli') or ocr_data.get('institution_name'):
        requirements['acceptance_letter'] = True
        score += 1
    
    # Check financial proof
    if (answers.get('has_gic') or answers.get('tuition_paid') or 
        ocr_data.get('gic_amount') or ocr_data.get('tuition_amount')):
        requirements['financial_proof'] = True
        score += 1
    
    # Check language test
    if (answers.get('has_language_test') or answers.get('all_scores_6_plus') or
        ocr_data.get('ielts_scores')):
        requirements['language_test'] = True
        score += 1
    
    # Check medical exam
    if answers.get('has_medical_exam'):
        requirements['medical_exam'] = True
        score += 1
    
    # Check criminal record
    if not answers.get('criminal_background', True):
        requirements['clean_criminal_record'] = True
        score += 1
    
    # Check passport
    if answers.get('passport_country_code') or ocr_data.get('passport_number'):
        requirements['valid_passport'] = True
        score += 1
    
    # Check provincial attestation
    if answers.get('has_provincial_attestation'):
        requirements['provincial_attestation'] = True
        score += 1
    
    eligibility_score = (score / max_score) * 100
    eligible = score >= 6  # Need at least 6/7 requirements
    
    requirements_met = [req for req, met in requirements.items() if met]
    requirements_missing = [req for req, met in requirements.items() if not met]
    
    recommendations = generate_recommendations(requirements_missing, answers)
    
    return {
        'eligible': eligible,
        'score': eligibility_score,
        'requirements_met': requirements_met,
        'requirements_missing': requirements_missing,
        'recommendations': recommendations
    }


def generate_recommendations(missing_requirements, answers):
    """Generate recommendations based on missing requirements."""
    recommendations = []
    
    if 'acceptance_letter' in missing_requirements:
        recommendations.append("Obtain an acceptance letter from a designated learning institution (DLI)")
    
    if 'financial_proof' in missing_requirements:
        recommendations.append("Provide proof of financial support (GIC, tuition payment, bank statements)")
    
    if 'language_test' in missing_requirements:
        recommendations.append("Take an approved language test (IELTS, CELPIP, TEF, or TCF)")
    
    if 'medical_exam' in missing_requirements:
        recommendations.append("Complete an upfront medical exam with an IRCC panel physician")
    
    if 'clean_criminal_record' in missing_requirements:
        recommendations.append("Obtain a police certificate from your country of residence")
    
    if 'valid_passport' in missing_requirements:
        recommendations.append("Ensure you have a valid passport with at least 6 months validity")
    
    if 'provincial_attestation' in missing_requirements:
        recommendations.append("Obtain a Provincial or Territorial Attestation Letter (PAL/TAL)")
    
    return recommendations 