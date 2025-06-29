import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

TABLE_ANSWERS = os.environ.get('TABLE_ANSWERS', 'visamate-ai-wizardanswers')
TABLE_DOCS = os.environ.get('TABLE_DOCS', 'visamate-ai-documents')
BUCKET_DRAFTS = os.environ.get('BUCKET_DRAFTS', 'visamate-documents/drafts')


def lambda_handler(event, context):
    """Generate and fill visa application forms."""
    try:
        logger.info(f"Filling forms for event: {json.dumps(event, default=str)}")
        
        user_id = event.get('user_id')
        session_id = event.get('session_id')
        answers = event.get('answers', {})
        ocr_data = event.get('ocr_data', {})
        eligible = event.get('eligibility', True)
        
        if not eligible:
            return {
                'statusCode': 400,
                'success': False,
                'message': 'User is not eligible for visa application'
            }
        
        # Generate forms
        forms_result = generate_application_forms(user_id, session_id, answers, ocr_data)
        
        return {
            'statusCode': 200,
            'success': True,
            'forms_generated': forms_result['forms_count'],
            'forms_urls': forms_result['forms_urls'],
            'completion_percentage': forms_result['completion_percentage'],
            'generated_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Form fill error: {str(e)}")
        return {
            'statusCode': 500,
            'success': False,
            'error': str(e)
        }


def generate_application_forms(user_id, session_id, answers, ocr_data):
    """Generate visa application forms with pre-filled data."""
    
    # Merge answers and OCR data
    merged_data = {**answers, **ocr_data}
    
    forms = {
        'IMM1294': generate_imm1294_form(merged_data),
        'IMM5645': generate_imm5645_form(merged_data),
        'IMM5257': generate_imm5257_form(merged_data) if needs_visitor_visa(merged_data) else None
    }
    
    # Remove None forms
    forms = {k: v for k, v in forms.items() if v is not None}
    
    # Save forms to S3
    forms_urls = {}
    for form_type, form_data in forms.items():
        s3_key = f"drafts/{user_id}/{session_id}/{form_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            bucket_name = BUCKET_DRAFTS.split('/')[0] if '/' in BUCKET_DRAFTS else BUCKET_DRAFTS
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(form_data, default=str, indent=2),
                ContentType='application/json'
            )
            
            forms_urls[form_type] = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"Saved {form_type} form to {s3_key}")
            
        except Exception as e:
            logger.error(f"Failed to save {form_type} form: {str(e)}")
    
    # Calculate completion percentage
    total_fields = sum(len(form.get('fields', {})) for form in forms.values())
    filled_fields = sum(
        len([v for v in form.get('fields', {}).values() if v]) 
        for form in forms.values()
    )
    
    completion_percentage = (filled_fields / total_fields * 100) if total_fields > 0 else 0
    
    return {
        'forms_count': len(forms),
        'forms_urls': forms_urls,
        'completion_percentage': completion_percentage,
        'total_fields': total_fields,
        'filled_fields': filled_fields
    }


def generate_imm1294_form(data):
    """Generate IMM1294 (Study Permit Application) form."""
    return {
        'form_type': 'IMM1294',
        'form_title': 'Application for Study Permit Made Outside Canada',
        'fields': {
            # Personal Information
            'family_name': data.get('family_name', ''),
            'given_names': data.get('given_names', ''),
            'date_of_birth': data.get('date_of_birth', ''),
            'country_of_birth': data.get('country_of_birth', ''),
            'citizenship': data.get('nationality', ''),
            'sex': data.get('sex', ''),
            'marital_status': data.get('marital_status', ''),
            
            # Contact Information
            'current_address': data.get('current_address', ''),
            'phone_number': data.get('phone_number', ''),
            'email': data.get('email', ''),
            
            # Passport Information
            'passport_number': data.get('passport_number', ''),
            'passport_issue_date': data.get('passport_issue_date', ''),
            'passport_expiry_date': data.get('passport_expiry_date', ''),
            
            # Education Information
            'institution_name': data.get('institution_name', ''),
            'program_name': data.get('program_name', ''),
            'field_of_study': data.get('field_of_study', ''),
            'program_start_date': data.get('program_start_date', ''),
            'program_duration': data.get('program_duration', ''),
            
            # Financial Information
            'tuition_fees': data.get('tuition_amount', ''),
            'living_expenses': data.get('living_expenses', ''),
            'funds_available': data.get('gic_amount', ''),
            
            # Language Test
            'language_test_type': data.get('test_type', ''),
            'language_test_results': json.dumps(data.get('ielts_scores', {})),
        },
        'completion_date': datetime.utcnow().isoformat(),
        'auto_filled': True
    }


def generate_imm5645_form(data):
    """Generate IMM5645 (Family Information) form."""
    return {
        'form_type': 'IMM5645',
        'form_title': 'Family Information',
        'fields': {
            # Applicant Information
            'applicant_name': f"{data.get('given_names', '')} {data.get('family_name', '')}",
            'applicant_date_of_birth': data.get('date_of_birth', ''),
            
            # Family Members (placeholder - would need actual family data)
            'spouse_name': data.get('spouse_name', ''),
            'spouse_date_of_birth': data.get('spouse_date_of_birth', ''),
            'children_count': data.get('children_count', 0),
            
            # Parents Information
            'father_name': data.get('father_name', ''),
            'father_date_of_birth': data.get('father_date_of_birth', ''),
            'mother_name': data.get('mother_name', ''),
            'mother_date_of_birth': data.get('mother_date_of_birth', ''),
        },
        'completion_date': datetime.utcnow().isoformat(),
        'auto_filled': True
    }


def generate_imm5257_form(data):
    """Generate IMM5257 (Temporary Resident Visa) form if needed."""
    return {
        'form_type': 'IMM5257',
        'form_title': 'Application for Temporary Resident Visa',
        'fields': {
            # Personal Information (similar to IMM1294)
            'family_name': data.get('family_name', ''),
            'given_names': data.get('given_names', ''),
            'date_of_birth': data.get('date_of_birth', ''),
            'citizenship': data.get('nationality', ''),
            
            # Purpose of Visit
            'purpose_of_visit': 'Study',
            'duration_of_stay': data.get('program_duration', ''),
            
            # Contact Information
            'current_address': data.get('current_address', ''),
            'phone_number': data.get('phone_number', ''),
            'email': data.get('email', ''),
        },
        'completion_date': datetime.utcnow().isoformat(),
        'auto_filled': True
    }


def needs_visitor_visa(data):
    """Determine if visitor visa (IMM5257) is needed."""
    # Countries that typically need visitor visa
    visa_required_countries = ['IND', 'CHN', 'PAK', 'BGD', 'NPL', 'LKA']
    
    country_code = data.get('passport_country_code', '').upper()
    return country_code in visa_required_countries 