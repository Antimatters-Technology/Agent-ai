"""
Unit tests for SOP Generator service.
Tests the AI-powered SOP generation functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from src.services.sop_service import SOPGenerator, SOPContext, sop_generator


@pytest.fixture
def sample_context():
    """Sample SOP context for testing."""
    return SOPContext(
        full_name="John Doe",
        age=25,
        nationality="Indian",
        current_location="Mumbai, India",
        highest_qualification="Bachelor's Degree",
        institution_name="University of Mumbai",
        graduation_year=2022,
        gpa_percentage=85.0,
        field_of_study="Computer Science",
        program_name="Master of Computer Science",
        institution_canada="University of Toronto",
        program_duration="2 years",
        intake_term="Fall 2024",
        tuition_fees=45000.0,
        work_experience_years=2,
        current_job_title="Software Developer",
        employer_name="Tech Corp",
        total_funds_available=75000.0,
        funding_source="Family savings and education loan",
        career_goals="To become a data scientist and contribute to AI research",
        return_intention="To return to India and start my own tech company",
        how_program_helps="This program will provide advanced knowledge in AI and machine learning"
    )


@pytest.fixture
def sop_gen():
    """SOP generator instance for testing."""
    return SOPGenerator()


class TestSOPGenerator:
    """Test cases for SOP Generator."""
    
    @pytest.mark.asyncio
    async def test_generate_sop_success(self, sop_gen, sample_context):
        """Test successful SOP generation."""
        result = await sop_gen.generate_sop(sample_context)
        
        assert "sop_content" in result
        assert "word_count" in result
        assert "readability_score" in result
        assert "generated_at" in result
        assert "template_used" in result
        
        # Check SOP content contains key information
        sop_content = result["sop_content"]
        assert sample_context.full_name in sop_content
        assert sample_context.program_name in sop_content
        assert sample_context.institution_canada in sop_content
        assert "STATEMENT OF PURPOSE" in sop_content.upper()
    
    @pytest.mark.asyncio
    async def test_generate_sop_with_gaps(self, sop_gen, sample_context):
        """Test SOP generation with education gaps."""
        sample_context.gaps_in_education = "Took a gap year to work and gain experience"
        
        result = await sop_gen.generate_sop(sample_context)
        
        assert result["template_used"] == "gap_year"
        assert "sop_content" in result
    
    @pytest.mark.asyncio
    async def test_generate_sop_career_change(self, sop_gen, sample_context):
        """Test SOP generation for career change scenario."""
        sample_context.work_experience_years = 5
        sample_context.gaps_in_education = None
        
        result = await sop_gen.generate_sop(sample_context)
        
        assert result["template_used"] == "career_change"
    
    def test_validate_context_success(self, sop_gen, sample_context):
        """Test successful context validation."""
        # Should not raise any exception
        sop_gen._validate_context(sample_context)
    
    def test_validate_context_missing_required_field(self, sop_gen, sample_context):
        """Test context validation with missing required field."""
        sample_context.full_name = ""
        
        with pytest.raises(ValueError, match="Required field 'full_name' is missing"):
            sop_gen._validate_context(sample_context)
    
    def test_select_template_standard(self, sop_gen, sample_context):
        """Test template selection for standard case."""
        template = sop_gen._select_template(sample_context, "standard")
        
        assert "Write a compelling Statement of Purpose" in template
        assert "INTRODUCTION" in template
        assert "ACADEMIC BACKGROUND" in template
    
    def test_select_template_gap_year(self, sop_gen, sample_context):
        """Test template selection for gap year case."""
        sample_context.gaps_in_education = "Gap year explanation"
        
        template = sop_gen._select_template(sample_context, "standard")
        
        assert "EXPLANATION OF GAPS" in template
    
    def test_context_to_string(self, sop_gen, sample_context):
        """Test context serialization to string."""
        context_str = sop_gen._context_to_string(sample_context)
        
        assert sample_context.full_name in context_str
        assert sample_context.program_name in context_str
        assert str(sample_context.tuition_fees) in context_str
        assert "Personal Information:" in context_str
        assert "Education:" in context_str
    
    def test_calculate_metrics(self, sop_gen):
        """Test SOP metrics calculation."""
        sample_content = """
        This is a test SOP content. It has multiple sentences. 
        The readability should be calculated correctly.
        This content has exactly four sentences.
        """
        
        metrics = sop_gen._calculate_metrics(sample_content)
        
        assert "word_count" in metrics
        assert "readability_score" in metrics
        assert "sections" in metrics
        assert "avg_sentence_length" in metrics
        
        assert metrics["word_count"] > 0
        assert isinstance(metrics["readability_score"], float)
    
    def test_post_process(self, sop_gen):
        """Test SOP content post-processing."""
        raw_content = """
        
        
        Line 1
        
        Line 2
        
        
        Line 3
        
        
        """
        
        processed = sop_gen._post_process(raw_content)
        
        # Should remove extra whitespace and format properly
        lines = processed.split('\n\n')
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"
    
    def test_generate_context_hash(self, sop_gen, sample_context):
        """Test context hash generation."""
        hash1 = sop_gen._generate_context_hash(sample_context)
        hash2 = sop_gen._generate_context_hash(sample_context)
        
        # Same context should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16
        
        # Different context should produce different hash
        sample_context.full_name = "Jane Doe"
        hash3 = sop_gen._generate_context_hash(sample_context)
        assert hash1 != hash3
    
    @pytest.mark.asyncio
    async def test_regenerate_section(self, sop_gen, sample_context):
        """Test section regeneration functionality."""
        original_sop = "Original SOP content"
        section_name = "ACADEMIC BACKGROUND"
        
        result = await sop_gen.regenerate_section(original_sop, section_name, sample_context)
        
        assert "Regenerated ACADEMIC BACKGROUND section" in result
    
    @pytest.mark.asyncio
    async def test_improve_sop(self, sop_gen, sample_context):
        """Test SOP improvement functionality."""
        original_sop = "Original SOP content"
        feedback = "Make it more compelling and add specific examples"
        
        result = await sop_gen.improve_sop(original_sop, feedback, sample_context)
        
        assert "Improved SOP based on: Make it more compelling" in result


class TestSOPContext:
    """Test cases for SOP Context model."""
    
    def test_sop_context_creation(self, sample_context):
        """Test SOP context creation with all fields."""
        assert sample_context.full_name == "John Doe"
        assert sample_context.age == 25
        assert sample_context.nationality == "Indian"
        assert sample_context.tuition_fees == 45000.0
        assert sample_context.work_experience_years == 2
    
    def test_sop_context_optional_fields(self):
        """Test SOP context with minimal required fields."""
        context = SOPContext(
            full_name="Jane Smith",
            age=24,
            nationality="Canadian",
            current_location="Toronto, Canada",
            highest_qualification="Bachelor's",
            institution_name="University of Toronto",
            graduation_year=2023,
            gpa_percentage=88.0,
            field_of_study="Engineering",
            program_name="Master of Engineering",
            institution_canada="McGill University",
            program_duration="1.5 years",
            intake_term="Winter 2024",
            tuition_fees=35000.0,
            work_experience_years=0,
            total_funds_available=50000.0,
            funding_source="Personal savings",
            career_goals="To become a professional engineer",
            return_intention="To work in Canada",
            how_program_helps="Will provide advanced technical skills"
        )
        
        assert context.current_job_title is None
        assert context.employer_name is None
        assert context.ielts_score is None
        assert context.gaps_in_education is None
        assert context.previous_visa_refusals is False


class TestGlobalSOPGenerator:
    """Test the global SOP generator instance."""
    
    def test_global_instance_exists(self):
        """Test that global SOP generator instance exists."""
        assert sop_generator is not None
        assert isinstance(sop_generator, SOPGenerator)
    
    @pytest.mark.asyncio
    async def test_global_instance_functionality(self, sample_context):
        """Test that global instance works correctly."""
        result = await sop_generator.generate_sop(sample_context)
        
        assert "sop_content" in result
        assert result["word_count"] > 0


@pytest.mark.integration
class TestSOPGeneratorIntegration:
    """Integration tests for SOP Generator."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_sop_generation(self, sample_context):
        """Test complete end-to-end SOP generation flow."""
        # Test the complete flow from context to final SOP
        result = await sop_generator.generate_sop(sample_context, "standard")
        
        # Verify all components are working together
        assert result["word_count"] > 100  # Reasonable SOP length
        assert result["readability_score"] > 0
        assert result["sections"] >= 0
        assert "STATEMENT OF PURPOSE" in result["sop_content"].upper()
        
        # Verify timestamp is recent
        generated_time = datetime.fromisoformat(result["generated_at"])
        time_diff = datetime.utcnow() - generated_time
        assert time_diff.total_seconds() < 60  # Generated within last minute 