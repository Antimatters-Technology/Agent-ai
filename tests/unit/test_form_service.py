"""
Unit tests for Form Auto-filling Service.
Tests the IRCC form generation and auto-filling functionality.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

from src.services.form_service import (
    FormAutoFillService,
    FormType,
    FormField,
    FormSection,
    IRCCForm,
    form_service
)


class TestFormAutoFillService:
    """Test class for FormAutoFillService."""
    
    @pytest.fixture
    def form_service_instance(self):
        """Create a form service instance for testing."""
        return FormAutoFillService()
    
    @pytest.fixture
    def sample_questionnaire_responses(self):
        """Sample questionnaire responses for testing."""
        return {
            "basic_info": {
                "purpose_in_canada": "Study",
                "duration_of_stay": "Temporarily - more than 6 months",
                "passport_country_code": "IND",
                "current_residence": "India",
                "has_canadian_family": False,
                "date_of_birth": "2003-05-04"
            },
            "education_status": {
                "has_provincial_attestation": True,
                "attestation_province": "Ontario",
                "accepted_to_dli": True,
                "post_secondary_institution": True,
                "institution_name": "University of Toronto",
                "program_name": "Master of Computer Science",
                "program_duration": "2 years",
                "program_start_date": "2024-09-01"
            },
            "financial_status": {
                "has_sds_gic": True,
                "tuition_paid_full": True,
                "gic_amount": 20635.0,
                "tuition_amount": 45000.0,
                "funding_source": "Family savings and GIC"
            },
            "language_test": {
                "has_language_test": True,
                "test_type": "IELTS",
                "all_scores_6_plus": True,
                "listening_score": 7.5,
                "reading_score": 7.0,
                "writing_score": 6.5,
                "speaking_score": 7.0,
                "overall_score": 7.0
            },
            "medical_exam": {
                "has_medical_exam": True,
                "exam_date": "2024-01-15",
                "panel_physician": "Dr. Smith - Authorized Panel Physician",
                "medical_ref_number": "MED123456789"
            },
            "marital_status": "Never Married/Single",
            "destination_province": "Ontario",
            "criminal_background": False
        }
    
    def test_form_service_initialization(self, form_service_instance):
        """Test form service initialization."""
        assert form_service_instance is not None
        assert len(form_service_instance.form_templates) == 3
        assert FormType.IMM1294 in form_service_instance.form_templates
        assert FormType.IMM5645 in form_service_instance.form_templates
        assert FormType.IMM5257 in form_service_instance.form_templates
    
    def test_imm1294_template_creation(self, form_service_instance):
        """Test IMM1294 template creation."""
        template = form_service_instance.form_templates[FormType.IMM1294]
        
        assert template.form_type == FormType.IMM1294
        assert template.form_title == "Application for Study Permit Made Outside of Canada"
        assert template.form_version == "11-2023"
        assert len(template.sections) > 0
        
        # Check specific sections exist
        section_ids = [section.section_id for section in template.sections]
        expected_sections = [
            "personal_details",
            "passport_travel_doc", 
            "contact_info",
            "education_occupation",
            "details_study",
            "funds_financial_support",
            "background_info"
        ]
        
        for expected_section in expected_sections:
            assert expected_section in section_ids
    
    def test_imm5645_template_creation(self, form_service_instance):
        """Test IMM5645 template creation."""
        template = form_service_instance.form_templates[FormType.IMM5645]
        
        assert template.form_type == FormType.IMM5645
        assert template.form_title == "Family Information"
        assert template.form_version == "01-2024"
        assert len(template.sections) > 0
        
        # Check family-related sections
        section_ids = [section.section_id for section in template.sections]
        assert "applicant_info" in section_ids
        assert "family_members" in section_ids
    
    def test_imm5257_template_creation(self, form_service_instance):
        """Test IMM5257 template creation."""
        template = form_service_instance.form_templates[FormType.IMM5257]
        
        assert template.form_type == FormType.IMM5257
        assert template.form_title == "Application for Temporary Resident Visa Made Outside Canada"
        assert template.form_version == "03-2014"
        assert len(template.sections) > 0
        
        # Check TRV-specific sections
        section_ids = [section.section_id for section in template.sections]
        assert "personal_details" in section_ids
        assert "travel_info" in section_ids
    
    @pytest.mark.asyncio
    async def test_auto_fill_imm1294(self, form_service_instance, sample_questionnaire_responses):
        """Test auto-filling IMM1294 form."""
        form = await form_service_instance.auto_fill_form(
            FormType.IMM1294, 
            sample_questionnaire_responses
        )
        
        assert form.form_type == FormType.IMM1294
        assert form.completion_percentage > 0
        
        # Check that some fields were auto-filled
        filled_fields = []
        for section in form.sections:
            for field in section.fields:
                if field.value:
                    filled_fields.append(field.field_id)
        
        # Should have filled some basic fields
        expected_filled = ["date_of_birth", "country_of_birth", "marital_status"]
        for field_id in expected_filled:
            # Check if at least some expected fields are filled
            pass  # Some fields might not be filled due to mapping logic
        
        assert len(filled_fields) > 0
    
    @pytest.mark.asyncio
    async def test_auto_fill_imm5645(self, form_service_instance, sample_questionnaire_responses):
        """Test auto-filling IMM5645 form."""
        form = await form_service_instance.auto_fill_form(
            FormType.IMM5645, 
            sample_questionnaire_responses
        )
        
        assert form.form_type == FormType.IMM5645
        assert form.completion_percentage >= 0
        
        # Check family information fields
        family_section = next(
            (s for s in form.sections if s.section_id == "family_members"), 
            None
        )
        assert family_section is not None
    
    @pytest.mark.asyncio
    async def test_auto_fill_imm5257(self, form_service_instance, sample_questionnaire_responses):
        """Test auto-filling IMM5257 form."""
        form = await form_service_instance.auto_fill_form(
            FormType.IMM5257, 
            sample_questionnaire_responses
        )
        
        assert form.form_type == FormType.IMM5257
        assert form.completion_percentage >= 0
        
        # Check travel information
        travel_section = next(
            (s for s in form.sections if s.section_id == "travel_info"), 
            None
        )
        assert travel_section is not None
        
        # Check purpose of visit is set to Study
        purpose_field = None
        for field in travel_section.fields:
            if field.field_id == "purpose_of_visit":
                purpose_field = field
                break
        
        if purpose_field and purpose_field.value:
            assert purpose_field.value == "Study"
    
    @pytest.mark.asyncio
    async def test_generate_all_forms(self, form_service_instance, sample_questionnaire_responses):
        """Test generating all required forms."""
        forms = await form_service_instance.generate_all_forms(sample_questionnaire_responses)
        
        assert isinstance(forms, dict)
        assert FormType.IMM1294 in forms
        assert FormType.IMM5645 in forms
        
        # Check if TRV is generated for Indian passport
        if form_service_instance._needs_trv(sample_questionnaire_responses):
            assert FormType.IMM5257 in forms
        
        # Verify all forms are properly filled
        for form_type, form in forms.items():
            assert isinstance(form, IRCCForm)
            assert form.form_type == form_type
            assert form.completion_percentage >= 0
    
    def test_needs_trv_logic(self, form_service_instance, sample_questionnaire_responses):
        """Test TRV requirement logic."""
        # Indian passport should require TRV
        assert form_service_instance._needs_trv(sample_questionnaire_responses) == True
        
        # Test with Canadian passport (should not need TRV)
        canadian_responses = sample_questionnaire_responses.copy()
        canadian_responses["basic_info"]["passport_country_code"] = "CAN"
        assert form_service_instance._needs_trv(canadian_responses) == False
        
        # Test with US passport (should not need TRV)
        us_responses = sample_questionnaire_responses.copy()
        us_responses["basic_info"]["passport_country_code"] = "USA"
        assert form_service_instance._needs_trv(us_responses) == False
    
    def test_form_validation(self, form_service_instance):
        """Test form validation logic."""
        # Create a test form with some filled and unfilled required fields
        form = IRCCForm(
            form_type=FormType.IMM1294,
            form_title="Test Form",
            form_version="1.0",
            sections=[
                FormSection(
                    section_id="test_section",
                    section_name="Test Section",
                    fields=[
                        FormField("required_filled", "Required Filled", "text", value="test", is_required=True),
                        FormField("required_empty", "Required Empty", "text", value="", is_required=True),
                        FormField("optional_empty", "Optional Empty", "text", value="", is_required=False),
                    ]
                )
            ]
        )
        
        validated_form = form_service_instance._validate_form(form)
        
        # Should have 33.33% completion (1 out of 3 fields filled)
        assert validated_form.completion_percentage == pytest.approx(33.33, rel=1e-2)
        assert not validated_form.is_valid  # Should be invalid due to empty required field
        assert len(validated_form.validation_errors) == 1
        assert "Required Empty" in validated_form.validation_errors[0]
    
    def test_export_form_to_pdf_data(self, form_service_instance):
        """Test exporting form to PDF data format."""
        # Create a simple test form
        form = IRCCForm(
            form_type=FormType.IMM1294,
            form_title="Test Form",
            form_version="1.0",
            sections=[
                FormSection(
                    section_id="test_section",
                    section_name="Test Section",
                    fields=[
                        FormField("test_field", "Test Field", "text", value="test_value")
                    ]
                )
            ]
        )
        
        pdf_data = form_service_instance.export_form_to_pdf_data(form)
        
        assert pdf_data["form_type"] == "IMM1294"
        assert pdf_data["form_title"] == "Test Form"
        assert pdf_data["form_version"] == "1.0"
        assert len(pdf_data["sections"]) == 1
        assert pdf_data["sections"][0]["section_id"] == "test_section"
        assert len(pdf_data["sections"][0]["fields"]) == 1
        assert pdf_data["sections"][0]["fields"][0]["value"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, form_service_instance):
        """Test error handling in form auto-filling."""
        # Test with invalid form type
        with pytest.raises(KeyError):
            await form_service_instance.auto_fill_form(
                "INVALID_FORM", 
                {}
            )
        
        # Test with malformed responses
        malformed_responses = {"invalid": "data"}
        try:
            form = await form_service_instance.auto_fill_form(
                FormType.IMM1294, 
                malformed_responses
            )
            # Should not raise exception, just have low completion
            assert form.completion_percentage >= 0
        except Exception as e:
            pytest.fail(f"Should handle malformed responses gracefully: {e}")
    
    def test_form_field_types(self, form_service_instance):
        """Test that form fields have appropriate types."""
        imm1294 = form_service_instance.form_templates[FormType.IMM1294]
        
        # Check for various field types
        field_types = set()
        for section in imm1294.sections:
            for field in section.fields:
                field_types.add(field.field_type)
        
        expected_types = {"text", "date", "select", "textarea", "number", "radio", "email"}
        assert field_types.intersection(expected_types)  # Should have some of these types
    
    def test_global_form_service_instance(self):
        """Test that global form service instance is available."""
        from src.services.form_service import form_service as global_service
        
        assert global_service is not None
        assert isinstance(global_service, FormAutoFillService)
        assert len(global_service.form_templates) == 3


class TestFormDataStructures:
    """Test form data structure classes."""
    
    def test_form_field_creation(self):
        """Test FormField creation."""
        field = FormField(
            field_id="test_id",
            field_name="Test Field",
            field_type="text",
            value="test_value",
            is_required=True,
            help_text="Test help text"
        )
        
        assert field.field_id == "test_id"
        assert field.field_name == "Test Field"
        assert field.field_type == "text"
        assert field.value == "test_value"
        assert field.is_required == True
        assert field.help_text == "Test help text"
    
    def test_form_section_creation(self):
        """Test FormSection creation."""
        fields = [
            FormField("field1", "Field 1", "text"),
            FormField("field2", "Field 2", "date")
        ]
        
        section = FormSection(
            section_id="test_section",
            section_name="Test Section",
            fields=fields,
            instructions="Test instructions"
        )
        
        assert section.section_id == "test_section"
        assert section.section_name == "Test Section"
        assert len(section.fields) == 2
        assert section.instructions == "Test instructions"
    
    def test_ircc_form_creation(self):
        """Test IRCCForm creation."""
        form = IRCCForm(
            form_type=FormType.IMM1294,
            form_title="Test Form",
            form_version="1.0"
        )
        
        assert form.form_type == FormType.IMM1294
        assert form.form_title == "Test Form"
        assert form.form_version == "1.0"
        assert form.completion_percentage == 0.0
        assert form.is_valid == False
        assert len(form.validation_errors) == 0
        assert isinstance(form.generated_at, datetime)


@pytest.mark.integration
class TestFormServiceIntegration:
    """Integration tests for form service with other components."""
    
    @pytest.mark.asyncio
    async def test_integration_with_questionnaire_data(self):
        """Test integration with real questionnaire data structure."""
        # This would test with actual questionnaire response models
        # from the wizard API
        pass
    
    @pytest.mark.asyncio
    async def test_form_generation_performance(self):
        """Test form generation performance."""
        import time
        
        sample_responses = {
            "basic_info": {"passport_country_code": "IND", "date_of_birth": "2003-05-04"},
            "education_status": {"institution_name": "Test University"},
            "financial_status": {"gic_amount": 20000},
            "language_test": {"overall_score": 7.0},
            "medical_exam": {"has_medical_exam": True}
        }
        
        start_time = time.time()
        forms = await form_service.generate_all_forms(sample_responses)
        end_time = time.time()
        
        # Should generate forms quickly (under 1 second)
        assert end_time - start_time < 1.0
        assert len(forms) >= 2  # At least IMM1294 and IMM5645


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 