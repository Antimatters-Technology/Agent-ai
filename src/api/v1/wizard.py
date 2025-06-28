"""
Wizard API for VisaMate AI platform.
Handles the complete IRCC questionnaire flow and document preparation.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, validator

from src.core.config import settings
from src.services.sop_service import sop_generator, SOPContext
from src.services.gemini_service import gemini_service
from src.services.form_service import form_service, FormType

router = APIRouter()
logger = logging.getLogger(__name__)


class QuestionnaireStep(str, Enum):
    """IRCC Questionnaire steps."""
    BASIC_INFO = "basic_info"
    PURPOSE_DURATION = "purpose_duration"
    COUNTRY_RESIDENCE = "country_residence"
    FAMILY_STATUS = "family_status"
    PERSONAL_DETAILS = "personal_details"
    PROVINCIAL_ATTESTATION = "provincial_attestation"
    US_RESIDENCE = "us_residence"
    EDUCATION_STATUS = "education_status"
    MEDICAL_EXAM = "medical_exam"
    FINANCIAL_PROOF = "financial_proof"
    LANGUAGE_TEST = "language_test"
    MARITAL_STATUS = "marital_status"
    DESTINATION = "destination"
    PERMITS_VISA = "permits_visa"
    WORK_STUDY = "work_study"
    SCHOLARSHIPS = "scholarships"
    CRIMINAL_BACKGROUND = "criminal_background"
    FAMILY_APPLICATION = "family_application"
    BIOMETRICS = "biometrics"
    FEES_PAYMENT = "fees_payment"
    DOCUMENT_UPLOAD = "document_upload"


class DocumentType(str, Enum):
    """Required document types for study permit application."""
    # Application Forms
    IMM1294 = "imm1294"  # Application for Study Permit
    IMM5645 = "imm5645"  # Family Information
    IMM5257 = "imm5257"  # Temporary Resident Visa (optional)
    
    # Supporting Documents
    EDUCATION_TRANSCRIPT = "education_transcript"
    GIC_PROOF = "gic_proof"
    TUITION_PAYMENT = "tuition_payment"
    IELTS_RESULTS = "ielts_results"
    ACCEPTANCE_LETTER = "acceptance_letter"
    PASSPORT = "passport"
    PAL_TAL = "pal_tal"  # Provincial/Territorial Attestation Letter
    DIGITAL_PHOTO = "digital_photo"
    MEDICAL_EXAM = "medical_exam"
    
    # Optional Documents
    CLIENT_INFO = "client_info"
    ADDITIONAL_DOCS = "additional_docs"


# Pydantic Models for IRCC Questionnaire Responses
class BasicInfoResponse(BaseModel):
    """Basic information from IRCC questionnaire."""
    purpose_in_canada: str = Field(default="Study", description="What would you like to do in Canada?")
    duration_of_stay: str = Field(default="Temporarily - more than 6 months", description="How long are you planning to stay?")
    passport_country_code: str = Field(..., description="Passport country code (e.g., IND)")
    current_residence: str = Field(..., description="Current country of residence")
    has_canadian_family: bool = Field(default=False, description="Family member who is Canadian citizen/PR")
    date_of_birth: date = Field(..., description="Date of birth")


class EducationStatusResponse(BaseModel):
    """Education and institution details."""
    has_provincial_attestation: bool = Field(default=True, description="Has provincial attestation letter")
    attestation_province: str = Field(default="Ontario", description="Province of attestation letter")
    accepted_to_dli: bool = Field(default=True, description="Accepted to designated learning institution")
    post_secondary_institution: bool = Field(default=True, description="Post-secondary DLI")
    
    # Institution details
    institution_name: Optional[str] = Field(None, description="Name of the institution")
    program_name: Optional[str] = Field(None, description="Program name")
    program_duration: Optional[str] = Field(None, description="Program duration")
    program_start_date: Optional[date] = Field(None, description="Program start date")


class FinancialStatusResponse(BaseModel):
    """Financial proof and requirements."""
    has_sds_gic: bool = Field(default=True, description="Has SDS eligible GIC")
    tuition_paid_full: bool = Field(default=True, description="First year tuition paid in full")
    gic_amount: Optional[float] = Field(None, description="GIC amount in CAD")
    tuition_amount: Optional[float] = Field(None, description="Tuition amount paid")
    funding_source: Optional[str] = Field(None, description="Source of funding")


class LanguageTestResponse(BaseModel):
    """Language test results."""
    has_language_test: bool = Field(default=True, description="Taken language test in past 2 years")
    test_type: str = Field(default="IELTS", description="Type of language test")
    all_scores_6_plus: bool = Field(default=True, description="All IELTS scores 6.0 or higher")
    
    # Individual scores
    listening_score: Optional[float] = Field(None, ge=0, le=9, description="IELTS Listening score")
    reading_score: Optional[float] = Field(None, ge=0, le=9, description="IELTS Reading score")
    writing_score: Optional[float] = Field(None, ge=0, le=9, description="IELTS Writing score")
    speaking_score: Optional[float] = Field(None, ge=0, le=9, description="IELTS Speaking score")
    overall_score: Optional[float] = Field(None, ge=0, le=9, description="Overall IELTS score")


class MedicalExamResponse(BaseModel):
    """Medical examination details."""
    has_medical_exam: bool = Field(default=True, description="Medical exam within 12 months")
    exam_date: Optional[date] = Field(None, description="Date of medical exam")
    panel_physician: Optional[str] = Field(None, description="Panel physician details")
    medical_ref_number: Optional[str] = Field(None, description="Medical reference number")


class IRCCQuestionnaireResponse(BaseModel):
    """Complete IRCC questionnaire response model."""
    # Basic Information
    basic_info: BasicInfoResponse
    
    # Education Status
    education_status: EducationStatusResponse
    
    # Financial Status
    financial_status: FinancialStatusResponse
    
    # Language Test
    language_test: LanguageTestResponse
    
    # Medical Exam
    medical_exam: MedicalExamResponse
    
    # Additional Fields
    marital_status: str = Field(default="Never Married/Single", description="Marital status")
    destination_province: str = Field(default="Ontario", description="Province of destination")
    
    # Background Checks
    has_valid_permits: bool = Field(default=False, description="Has valid work/study permit")
    is_exchange_student: bool = Field(default=False, description="Exchange student")
    work_essential_to_studies: bool = Field(default=False, description="Work essential to studies")
    has_family_in_canada: bool = Field(default=False, description="Family member with status in Canada")
    has_scholarship: bool = Field(default=False, description="Commonwealth/CIDA scholarship")
    criminal_background: bool = Field(default=False, description="Criminal background")
    wants_family_application: bool = Field(default=False, description="Family member application")
    giving_access_to_application: bool = Field(default=False, description="Giving access to application")
    has_biometrics: bool = Field(default=False, description="Biometrics in past 10 years")
    will_pay_fees: bool = Field(default=True, description="Will pay application fees")
    can_scan_documents: bool = Field(default=True, description="Can scan documents")
    pay_online: bool = Field(default=True, description="Pay fees online")


class DocumentChecklistItem(BaseModel):
    """Individual document checklist item."""
    document_type: DocumentType
    document_name: str
    is_required: bool
    is_uploaded: bool = False
    file_path: Optional[str] = None
    upload_date: Optional[datetime] = None
    file_size: Optional[int] = None
    instructions: Optional[str] = None


class DocumentChecklist(BaseModel):
    """Complete document checklist for study permit application."""
    application_forms: List[DocumentChecklistItem] = []
    supporting_documents: List[DocumentChecklistItem] = []
    optional_documents: List[DocumentChecklistItem] = []
    total_fee_cad: float = 235.00  # Study Permit ($150) + Biometrics ($85)


class WizardSession(BaseModel):
    """Wizard session model for tracking user progress."""
    session_id: str
    user_id: str
    current_step: QuestionnaireStep
    questionnaire_responses: Optional[IRCCQuestionnaireResponse] = None
    document_checklist: Optional[DocumentChecklist] = None
    created_at: datetime
    updated_at: datetime
    is_complete: bool = False
    sop_generated: bool = False
    forms_prefilled: bool = False


class QuestionnaireRequest(BaseModel):
    """Request to update questionnaire responses."""
    responses: IRCCQuestionnaireResponse


class DocumentUploadRequest(BaseModel):
    """Request for document upload."""
    document_type: DocumentType
    file_name: str
    file_content: str  # Base64 encoded


# API Endpoints

@router.post("/start", response_model=WizardSession)
async def start_wizard_session(user_id: str = "anonymous"):
    """Start a new wizard session for IRCC application."""
    try:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
        
        # Create document checklist
        document_checklist = create_document_checklist()
        
        session = WizardSession(
            session_id=session_id,
            user_id=user_id,
            current_step=QuestionnaireStep.BASIC_INFO,
            document_checklist=document_checklist,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        logger.info(f"Started wizard session: {session_id}")
        return session
        
    except Exception as e:
        logger.error(f"Failed to start wizard session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start wizard session: {str(e)}"
        )


@router.post("/questionnaire/{session_id}", response_model=WizardSession)
async def submit_questionnaire(session_id: str, request: QuestionnaireRequest):
    """Submit or update questionnaire responses."""
    try:
        # Validate and process questionnaire responses
        responses = request.responses
        
        # Auto-fill forms based on responses
        prefilled_forms = await auto_fill_forms(responses)
        
        # Generate SOP context from responses
        sop_context = create_sop_context_from_questionnaire(responses)
        
        # Update session
        updated_session = WizardSession(
            session_id=session_id,
            user_id="user",  # Should come from auth
            current_step=QuestionnaireStep.DOCUMENT_UPLOAD,
            questionnaire_responses=responses,
            document_checklist=create_document_checklist(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            forms_prefilled=True
        )
        
        logger.info(f"Updated questionnaire for session: {session_id}")
        return updated_session
        
    except Exception as e:
        logger.error(f"Failed to submit questionnaire: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to submit questionnaire: {str(e)}"
        )


@router.post("/generate-sop/{session_id}")
async def generate_sop_from_questionnaire(session_id: str):
    """Generate SOP based on questionnaire responses."""
    try:
        # This would typically fetch session from database
        # For now, return a sample response
        
        # Create sample SOP context from questionnaire
        sample_context = SOPContext(
            full_name="John Doe",
            age=21,
            nationality="Indian",
            current_location="Mumbai, India",
            highest_qualification="Bachelor's Degree",
            institution_name="University of Mumbai",
            graduation_year=2024,
            gpa_percentage=85.0,
            field_of_study="Computer Science",
            program_name="Master of Computer Science",
            institution_canada="University of Toronto",
            program_duration="2 years",
            intake_term="Fall 2024",
            tuition_fees=45000.0,
            work_experience_years=0,
            total_funds_available=75000.0,
            funding_source="Family savings and GIC",
            career_goals="To become a software engineer and contribute to AI research",
            return_intention="To return to India and start my own tech company",
            how_program_helps="This program will provide advanced knowledge in AI and machine learning",
            ties_to_home_country="Strong family ties and property ownership in India"
        )
        
        # Generate SOP
        sop_result = await sop_generator.generate_sop(sample_context, "standard")
        
        return {
            "session_id": session_id,
            "sop_generated": True,
            "sop_content": sop_result["sop_content"],
            "word_count": sop_result["word_count"],
            "quality_score": sop_result["quality_score"],
            "meets_requirements": sop_result["meets_requirements"]
        }
        
    except Exception as e:
        logger.error(f"Failed to generate SOP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate SOP: {str(e)}"
        )


@router.get("/document-checklist/{session_id}", response_model=DocumentChecklist)
async def get_document_checklist(session_id: str):
    """Get document checklist for the session."""
    try:
        checklist = create_document_checklist()
        return checklist
        
    except Exception as e:
        logger.error(f"Failed to get document checklist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document checklist: {str(e)}"
        )


@router.post("/upload-document/{session_id}")
async def upload_document(session_id: str, request: DocumentUploadRequest):
    """Upload a document for the application."""
    try:
        # Process document upload
        # This would typically save to S3 and update database
        
        return {
            "session_id": session_id,
            "document_type": request.document_type,
            "file_name": request.file_name,
            "uploaded": True,
            "upload_time": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Failed to upload document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/prefilled-forms/{session_id}")
async def get_prefilled_forms(session_id: str):
    """Get auto-filled forms based on questionnaire responses."""
    try:
        # In a real implementation, this would fetch the session from database
        # For now, return sample prefilled forms
        
        # Sample questionnaire responses for demonstration
        sample_responses = IRCCQuestionnaireResponse(
            basic_info=BasicInfoResponse(
                passport_country_code="IND",
                current_residence="India",
                date_of_birth=date(2003, 5, 4)
            ),
            education_status=EducationStatusResponse(
                institution_name="University of Toronto",
                program_name="Master of Computer Science",
                program_duration="2 years",
                program_start_date=date(2024, 9, 1)
            ),
            financial_status=FinancialStatusResponse(
                gic_amount=20635.0,
                tuition_amount=45000.0,
                funding_source="Family savings and GIC"
            ),
            language_test=LanguageTestResponse(
                listening_score=7.5,
                reading_score=7.0,
                writing_score=6.5,
                speaking_score=7.0,
                overall_score=7.0
            ),
            medical_exam=MedicalExamResponse(
                exam_date=date(2024, 1, 15),
                panel_physician="Dr. Smith - Authorized Panel Physician",
                medical_ref_number="MED123456789"
            )
        )
        
        # Generate prefilled forms
        prefilled_data = await auto_fill_forms(sample_responses)
        
        return {
            "session_id": session_id,
            "prefilled_forms": prefilled_data,
            "prefilled_at": datetime.utcnow(),
            "instructions": {
                "IMM1294": "Review and complete remaining fields in the Study Permit application",
                "IMM5645": "Verify family information and add missing details",
                "IMM5257": "Complete if you need a Temporary Resident Visa"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get prefilled forms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prefilled forms: {str(e)}"
        )


# Helper Functions

def create_document_checklist() -> DocumentChecklist:
    """Create the standard document checklist for study permit application."""
    
    # Application Forms
    application_forms = [
        DocumentChecklistItem(
            document_type=DocumentType.IMM1294,
            document_name="Application for Study Permit Made Outside of Canada (IMM1294)",
            is_required=True,
            instructions="Complete all sections of the form"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.IMM5645,
            document_name="Family Information (IMM5645)",
            is_required=True,
            instructions="Provide information about all family members"
        )
    ]
    
    # Supporting Documents
    supporting_documents = [
        DocumentChecklistItem(
            document_type=DocumentType.EDUCATION_TRANSCRIPT,
            document_name="Recent Education Transcript",
            is_required=True,
            instructions="Official transcripts from your most recent education"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.GIC_PROOF,
            document_name="Proof of Guaranteed Investment Certificate (GIC)",
            is_required=True,
            instructions="GIC certificate from a participating Canadian financial institution"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.TUITION_PAYMENT,
            document_name="Proof of tuition payment",
            is_required=True,
            instructions="Receipt showing first year tuition payment"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.IELTS_RESULTS,
            document_name="Proof of IELTS language test results",
            is_required=True,
            instructions="Official IELTS test results with all scores 6.0 or higher"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.ACCEPTANCE_LETTER,
            document_name="Letter of Acceptance or Letter of Enrollment / Registration",
            is_required=True,
            instructions="Official letter from designated learning institution"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.PASSPORT,
            document_name="Passport",
            is_required=True,
            instructions="Valid passport with at least 6 months validity"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.PAL_TAL,
            document_name="Provincial or Territorial Attestation Letter (PAL or TAL)",
            is_required=True,
            instructions="Attestation letter from the province/territory"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.DIGITAL_PHOTO,
            document_name="Digital photo",
            is_required=True,
            instructions="Recent digital photograph meeting IRCC specifications"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.MEDICAL_EXAM,
            document_name="Proof of upfront medical exam",
            is_required=True,
            instructions="Medical exam results from IRCC panel physician"
        )
    ]
    
    # Optional Documents
    optional_documents = [
        DocumentChecklistItem(
            document_type=DocumentType.IMM5257,
            document_name="Schedule 1 - Application for a Temporary Resident Visa Made Outside Canada (IMM 5257)",
            is_required=False,
            instructions="Complete if you need a visitor visa"
        ),
        DocumentChecklistItem(
            document_type=DocumentType.CLIENT_INFO,
            document_name="Client Information",
            is_required=False,
            instructions="Additional client information if applicable"
        )
    ]
    
    return DocumentChecklist(
        application_forms=application_forms,
        supporting_documents=supporting_documents,
        optional_documents=optional_documents
    )


async def auto_fill_forms(responses: IRCCQuestionnaireResponse) -> Dict[str, Any]:
    """Auto-fill IRCC forms based on questionnaire responses."""
    try:
        # Convert Pydantic model to dict for form service
        responses_dict = responses.dict()
        
        # Generate all required forms
        forms = await form_service.generate_all_forms(responses_dict)
        
        # Convert forms to response format
        form_data = {}
        for form_type, form in forms.items():
            form_data[form_type.value] = {
                "form_title": form.form_title,
                "form_version": form.form_version,
                "completion_percentage": form.completion_percentage,
                "is_valid": form.is_valid,
                "validation_errors": form.validation_errors,
                "pdf_data": form_service.export_form_to_pdf_data(form)
            }
        
        return {
            "forms": form_data,
            "total_forms": len(forms),
            "prefilled_fields": sum(len(form.sections) for form in forms.values()),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to auto-fill forms: {str(e)}")
        # Return fallback response
        return {
            "forms": {
                "IMM1294": {"form_title": "Study Permit Application", "completion_percentage": 0},
                "IMM5645": {"form_title": "Family Information", "completion_percentage": 0}
            },
            "error": f"Form auto-fill failed: {str(e)}"
        }


def create_sop_context_from_questionnaire(responses: IRCCQuestionnaireResponse) -> SOPContext:
    """Create SOP context from questionnaire responses."""
    return SOPContext(
        full_name="Applicant Name",  # Would come from user profile
        age=datetime.now().year - responses.basic_info.date_of_birth.year,
        nationality=responses.basic_info.passport_country_code,
        current_location=responses.basic_info.current_residence,
        highest_qualification="Bachelor's Degree",  # From education status
        institution_name=responses.education_status.institution_name or "Previous Institution",
        graduation_year=2024,  # Would be calculated
        gpa_percentage=85.0,  # Would come from transcripts
        field_of_study="Computer Science",  # From education background
        program_name=responses.education_status.program_name or "Graduate Program",
        institution_canada=responses.education_status.institution_name or "Canadian Institution",
        program_duration=responses.education_status.program_duration or "2 years",
        intake_term="Fall 2024",  # From program start date
        tuition_fees=responses.financial_status.tuition_amount or 45000.0,
        work_experience_years=0,  # Would come from work history
        total_funds_available=responses.financial_status.gic_amount or 75000.0,
        funding_source=responses.financial_status.funding_source or "GIC and family support",
        career_goals="To advance my career in my field of study",
        return_intention="To return to my home country and contribute to its development",
        how_program_helps="This program will provide me with advanced knowledge and skills",
        ties_to_home_country="Strong family ties and career opportunities in home country",
        ielts_score=responses.language_test.overall_score
    ) 