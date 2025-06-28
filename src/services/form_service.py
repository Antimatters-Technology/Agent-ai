"""
Form Auto-filling Service for IRCC Applications.
Handles auto-population of Canadian immigration forms based on questionnaire responses.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FormType(str, Enum):
    """IRCC Form types."""
    IMM1294 = "IMM1294"  # Application for Study Permit Made Outside of Canada
    IMM5645 = "IMM5645"  # Family Information
    IMM5257 = "IMM5257"  # Application for Temporary Resident Visa Made Outside Canada


@dataclass
class FormField:
    """Represents a form field with its metadata."""
    field_id: str
    field_name: str
    field_type: str  # text, date, checkbox, select, etc.
    value: Optional[str] = None
    is_required: bool = True
    validation_rules: Optional[Dict[str, Any]] = None
    help_text: Optional[str] = None


@dataclass
class FormSection:
    """Represents a section of a form."""
    section_id: str
    section_name: str
    fields: List[FormField] = field(default_factory=list)
    instructions: Optional[str] = None


@dataclass
class IRCCForm:
    """Represents a complete IRCC form."""
    form_type: FormType
    form_title: str
    form_version: str
    sections: List[FormSection] = field(default_factory=list)
    completion_percentage: float = 0.0
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class FormAutoFillService:
    """Service for auto-filling IRCC forms based on questionnaire responses."""
    
    def __init__(self):
        self.form_templates = self._initialize_form_templates()
    
    def _initialize_form_templates(self) -> Dict[FormType, IRCCForm]:
        """Initialize form templates with their structure."""
        templates = {}
        
        # IMM1294 - Study Permit Application
        templates[FormType.IMM1294] = self._create_imm1294_template()
        
        # IMM5645 - Family Information
        templates[FormType.IMM5645] = self._create_imm5645_template()
        
        # IMM5257 - Temporary Resident Visa
        templates[FormType.IMM5257] = self._create_imm5257_template()
        
        return templates
    
    def _create_imm1294_template(self) -> IRCCForm:
        """Create IMM1294 form template."""
        sections = [
            FormSection(
                section_id="personal_details",
                section_name="Personal Details",
                instructions="Provide your personal information as it appears on your passport",
                fields=[
                    FormField("family_name", "Family name (surname)", "text", is_required=True),
                    FormField("given_names", "Given name(s) (first name)", "text", is_required=True),
                    FormField("other_names", "Other names (if applicable)", "text", is_required=False),
                    FormField("date_of_birth", "Date of birth", "date", is_required=True),
                    FormField("country_of_birth", "Country of birth", "select", is_required=True),
                    FormField("place_of_birth", "Place of birth (city/town)", "text", is_required=True),
                    FormField("sex", "Sex", "select", is_required=True),
                    FormField("marital_status", "Marital status", "select", is_required=True),
                ]
            ),
            FormSection(
                section_id="passport_travel_doc",
                section_name="Passport or Travel Document",
                instructions="Provide details of your current passport or travel document",
                fields=[
                    FormField("passport_number", "Passport/Document number", "text", is_required=True),
                    FormField("passport_country", "Country of issue", "select", is_required=True),
                    FormField("passport_issue_date", "Date of issue", "date", is_required=True),
                    FormField("passport_expiry_date", "Date of expiry", "date", is_required=True),
                ]
            ),
            FormSection(
                section_id="contact_info",
                section_name="Contact Information",
                instructions="Provide your current contact information",
                fields=[
                    FormField("mailing_address", "Mailing address", "textarea", is_required=True),
                    FormField("residential_address", "Residential address", "textarea", is_required=True),
                    FormField("telephone", "Telephone number", "text", is_required=True),
                    FormField("email", "Email address", "email", is_required=True),
                ]
            ),
            FormSection(
                section_id="education_occupation",
                section_name="Education and Occupation",
                instructions="Provide details about your education and current occupation",
                fields=[
                    FormField("education_level", "Level of education", "select", is_required=True),
                    FormField("current_occupation", "Current occupation", "text", is_required=True),
                    FormField("intended_occupation", "Intended occupation in Canada", "text", is_required=True),
                ]
            ),
            FormSection(
                section_id="details_study",
                section_name="Details of Study",
                instructions="Provide information about your intended studies in Canada",
                fields=[
                    FormField("level_of_study", "Level of study", "select", is_required=True),
                    FormField("field_of_study", "Field of study", "text", is_required=True),
                    FormField("institution_name", "Name of institution", "text", is_required=True),
                    FormField("institution_address", "Address of institution", "textarea", is_required=True),
                    FormField("program_duration", "Duration of program", "text", is_required=True),
                    FormField("program_start_date", "Program start date", "date", is_required=True),
                    FormField("tuition_fees", "Tuition fees (CAD)", "number", is_required=True),
                ]
            ),
            FormSection(
                section_id="funds_financial_support",
                section_name="Funds and Financial Support",
                instructions="Provide details about your financial support for studies",
                fields=[
                    FormField("funds_available", "Funds available for my stay (CAD)", "number", is_required=True),
                    FormField("source_of_funds", "Source of funds", "textarea", is_required=True),
                    FormField("scholarship", "Scholarship/Fellowship details", "textarea", is_required=False),
                ]
            ),
            FormSection(
                section_id="background_info",
                section_name="Background Information",
                instructions="Answer all questions truthfully",
                fields=[
                    FormField("previous_study_permit", "Have you previously applied for a study permit?", "radio", is_required=True),
                    FormField("refused_visa", "Have you been refused a visa or permit?", "radio", is_required=True),
                    FormField("medical_exam", "Have you had a medical exam?", "radio", is_required=True),
                    FormField("criminal_charges", "Have you ever been charged with a criminal offence?", "radio", is_required=True),
                ]
            )
        ]
        
        return IRCCForm(
            form_type=FormType.IMM1294,
            form_title="Application for Study Permit Made Outside of Canada",
            form_version="11-2023",
            sections=sections
        )
    
    def _create_imm5645_template(self) -> IRCCForm:
        """Create IMM5645 form template."""
        sections = [
            FormSection(
                section_id="applicant_info",
                section_name="Applicant Information",
                instructions="Provide information about yourself",
                fields=[
                    FormField("family_name", "Family name", "text", is_required=True),
                    FormField("given_names", "Given names", "text", is_required=True),
                    FormField("date_of_birth", "Date of birth", "date", is_required=True),
                    FormField("place_of_birth", "Place of birth", "text", is_required=True),
                ]
            ),
            FormSection(
                section_id="family_members",
                section_name="Family Members",
                instructions="List all family members, whether accompanying you or not",
                fields=[
                    FormField("spouse_info", "Spouse information", "textarea", is_required=False),
                    FormField("children_info", "Children information", "textarea", is_required=False),
                    FormField("parents_info", "Parents information", "textarea", is_required=True),
                    FormField("siblings_info", "Siblings information", "textarea", is_required=False),
                ]
            )
        ]
        
        return IRCCForm(
            form_type=FormType.IMM5645,
            form_title="Family Information",
            form_version="01-2024",
            sections=sections
        )
    
    def _create_imm5257_template(self) -> IRCCForm:
        """Create IMM5257 form template."""
        sections = [
            FormSection(
                section_id="personal_details",
                section_name="Personal Details",
                instructions="Provide your personal information",
                fields=[
                    FormField("family_name", "Family name", "text", is_required=True),
                    FormField("given_names", "Given names", "text", is_required=True),
                    FormField("date_of_birth", "Date of birth", "date", is_required=True),
                    FormField("country_of_birth", "Country of birth", "select", is_required=True),
                ]
            ),
            FormSection(
                section_id="travel_info",
                section_name="Travel Information",
                instructions="Provide details about your intended travel to Canada",
                fields=[
                    FormField("purpose_of_visit", "Purpose of visit", "select", is_required=True),
                    FormField("intended_date_arrival", "Intended date of arrival", "date", is_required=True),
                    FormField("intended_length_stay", "Intended length of stay", "text", is_required=True),
                ]
            )
        ]
        
        return IRCCForm(
            form_type=FormType.IMM5257,
            form_title="Application for Temporary Resident Visa Made Outside Canada",
            form_version="03-2014",
            sections=sections
        )
    
    async def auto_fill_form(
        self, 
        form_type: FormType, 
        questionnaire_responses: Dict[str, Any]
    ) -> IRCCForm:
        """Auto-fill a form based on questionnaire responses."""
        try:
            # Get form template
            form = self._get_form_template(form_type)
            
            # Auto-fill based on form type
            if form_type == FormType.IMM1294:
                form = await self._auto_fill_imm1294(form, questionnaire_responses)
            elif form_type == FormType.IMM5645:
                form = await self._auto_fill_imm5645(form, questionnaire_responses)
            elif form_type == FormType.IMM5257:
                form = await self._auto_fill_imm5257(form, questionnaire_responses)
            
            # Validate form
            form = self._validate_form(form)
            
            logger.info(f"Auto-filled form {form_type.value} with {form.completion_percentage:.1f}% completion")
            return form
            
        except Exception as e:
            logger.error(f"Failed to auto-fill form {form_type.value}: {str(e)}")
            raise
    
    def _get_form_template(self, form_type: FormType) -> IRCCForm:
        """Get a copy of the form template."""
        import copy
        return copy.deepcopy(self.form_templates[form_type])
    
    async def _auto_fill_imm1294(
        self, 
        form: IRCCForm, 
        responses: Dict[str, Any]
    ) -> IRCCForm:
        """Auto-fill IMM1294 form with questionnaire responses."""
        
        # Extract data from responses
        basic_info = responses.get("basic_info", {})
        education_status = responses.get("education_status", {})
        financial_status = responses.get("financial_status", {})
        language_test = responses.get("language_test", {})
        medical_exam = responses.get("medical_exam", {})
        
        # Auto-fill mappings
        field_mappings = {
            # Personal Details
            "date_of_birth": basic_info.get("date_of_birth"),
            "country_of_birth": basic_info.get("passport_country_code"),
            "marital_status": responses.get("marital_status", "Never Married/Single"),
            
            # Passport Information
            "passport_country": basic_info.get("passport_country_code"),
            
            # Education and Study Details
            "institution_name": education_status.get("institution_name"),
            "program_duration": education_status.get("program_duration"),
            "program_start_date": education_status.get("program_start_date"),
            "tuition_fees": financial_status.get("tuition_amount"),
            
            # Financial Information
            "funds_available": financial_status.get("gic_amount"),
            "source_of_funds": financial_status.get("funding_source"),
            
            # Background Information
            "medical_exam": "Yes" if medical_exam.get("has_medical_exam") else "No",
            "criminal_charges": "No" if not responses.get("criminal_background") else "Yes",
        }
        
        # Apply mappings to form fields
        for section in form.sections:
            for field in section.fields:
                if field.field_id in field_mappings and field_mappings[field.field_id]:
                    field.value = str(field_mappings[field.field_id])
        
        return form
    
    async def _auto_fill_imm5645(
        self, 
        form: IRCCForm, 
        responses: Dict[str, Any]
    ) -> IRCCForm:
        """Auto-fill IMM5645 form with questionnaire responses."""
        
        basic_info = responses.get("basic_info", {})
        
        # Auto-fill mappings for family information
        field_mappings = {
            "date_of_birth": basic_info.get("date_of_birth"),
            "place_of_birth": basic_info.get("current_residence"),
            # Family members would need additional questionnaire data
            "spouse_info": "Not applicable" if responses.get("marital_status") == "Never Married/Single" else "",
            "parents_info": "To be provided based on family questionnaire",
        }
        
        # Apply mappings
        for section in form.sections:
            for field in section.fields:
                if field.field_id in field_mappings and field_mappings[field.field_id]:
                    field.value = str(field_mappings[field.field_id])
        
        return form
    
    async def _auto_fill_imm5257(
        self, 
        form: IRCCForm, 
        responses: Dict[str, Any]
    ) -> IRCCForm:
        """Auto-fill IMM5257 form with questionnaire responses."""
        
        basic_info = responses.get("basic_info", {})
        education_status = responses.get("education_status", {})
        
        # Auto-fill mappings for TRV
        field_mappings = {
            "date_of_birth": basic_info.get("date_of_birth"),
            "country_of_birth": basic_info.get("passport_country_code"),
            "purpose_of_visit": "Study",
            "intended_date_arrival": education_status.get("program_start_date"),
            "intended_length_stay": education_status.get("program_duration"),
        }
        
        # Apply mappings
        for section in form.sections:
            for field in section.fields:
                if field.field_id in field_mappings and field_mappings[field.field_id]:
                    field.value = str(field_mappings[field.field_id])
        
        return form
    
    def _validate_form(self, form: IRCCForm) -> IRCCForm:
        """Validate form completeness and data integrity."""
        total_fields = 0
        completed_fields = 0
        validation_errors = []
        
        for section in form.sections:
            for field in section.fields:
                total_fields += 1
                
                if field.value and field.value.strip():
                    completed_fields += 1
                elif field.is_required:
                    validation_errors.append(f"Required field '{field.field_name}' is empty")
        
        # Calculate completion percentage
        form.completion_percentage = (completed_fields / total_fields * 100) if total_fields > 0 else 0
        
        # Set validation status
        form.is_valid = len(validation_errors) == 0
        form.validation_errors = validation_errors
        
        return form
    
    async def generate_all_forms(
        self, 
        questionnaire_responses: Dict[str, Any]
    ) -> Dict[FormType, IRCCForm]:
        """Generate all required forms based on questionnaire responses."""
        forms = {}
        
        # Always generate IMM1294 (Study Permit)
        forms[FormType.IMM1294] = await self.auto_fill_form(
            FormType.IMM1294, 
            questionnaire_responses
        )
        
        # Always generate IMM5645 (Family Information)
        forms[FormType.IMM5645] = await self.auto_fill_form(
            FormType.IMM5645, 
            questionnaire_responses
        )
        
        # Generate IMM5257 (TRV) if needed
        # This would be based on questionnaire logic
        if self._needs_trv(questionnaire_responses):
            forms[FormType.IMM5257] = await self.auto_fill_form(
                FormType.IMM5257, 
                questionnaire_responses
            )
        
        return forms
    
    def _needs_trv(self, responses: Dict[str, Any]) -> bool:
        """Determine if applicant needs a Temporary Resident Visa."""
        # This would be based on passport country and other factors
        passport_country = responses.get("basic_info", {}).get("passport_country_code")
        
        # Countries that typically need TRV (simplified logic)
        trv_required_countries = ["IND", "CHN", "PAK", "BGD", "NGA"]
        
        return passport_country in trv_required_countries
    
    def export_form_to_pdf_data(self, form: IRCCForm) -> Dict[str, Any]:
        """Export form data in a format suitable for PDF generation."""
        pdf_data = {
            "form_type": form.form_type.value,
            "form_title": form.form_title,
            "form_version": form.form_version,
            "generated_at": form.generated_at.isoformat(),
            "completion_percentage": form.completion_percentage,
            "is_valid": form.is_valid,
            "validation_errors": form.validation_errors,
            "sections": []
        }
        
        for section in form.sections:
            section_data = {
                "section_id": section.section_id,
                "section_name": section.section_name,
                "instructions": section.instructions,
                "fields": []
            }
            
            for field in section.fields:
                field_data = {
                    "field_id": field.field_id,
                    "field_name": field.field_name,
                    "field_type": field.field_type,
                    "value": field.value or "",
                    "is_required": field.is_required,
                    "help_text": field.help_text
                }
                section_data["fields"].append(field_data)
            
            pdf_data["sections"].append(section_data)
        
        return pdf_data


# Global service instance
form_service = FormAutoFillService() 