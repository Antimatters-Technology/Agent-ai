"""
SOP (Statement of Purpose) Generator Service for VisaMate AI platform.
Generates personalized SOP documents for Canada study visa applications using Gemini AI.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import logging
from dataclasses import dataclass

from src.core.config import settings
from src.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


@dataclass
class SOPContext:
    """Context data for SOP generation."""
    # Personal Information
    full_name: str
    age: int
    nationality: str
    current_location: str
    
    # Educational Background
    highest_qualification: str
    institution_name: str
    graduation_year: int
    gpa_percentage: float
    field_of_study: str
    
    # Proposed Study in Canada
    program_name: str
    institution_canada: str
    program_duration: str
    intake_term: str
    tuition_fees: float
    
    # Work Experience
    work_experience_years: int
    
    # Financial Information
    total_funds_available: float
    funding_source: str
    
    # Future Plans
    career_goals: str
    return_intention: str
    how_program_helps: str
    
    # Optional fields
    sponsor_relationship: Optional[str] = None
    current_job_title: Optional[str] = None
    employer_name: Optional[str] = None
    relevant_experience: Optional[str] = None
    ielts_score: Optional[float] = None
    english_proficiency: str = "Intermediate"
    gaps_in_education: Optional[str] = None
    previous_visa_refusals: bool = False
    ties_to_home_country: str = ""
    academic_achievements: Optional[str] = None
    family_income: Optional[float] = None
    marital_status: str = "Single"
    program_level: str = "Graduate"
    specialization: Optional[str] = None


class SOPGenerator:
    """AI-powered SOP generator for Canada study visa applications using Gemini."""
    
    def __init__(self):
        self.model_name = settings.DEFAULT_LLM_MODEL
        self.max_retries = 3
        self.gemini_service = gemini_service
    
    async def generate_sop(self, context: SOPContext, template_type: str = "standard") -> Dict[str, Any]:
        """Generate a complete SOP document using Gemini AI."""
        try:
            # Validate context
            self._validate_context(context)
            
            # Convert context to dictionary for Gemini service
            context_dict = self._context_to_dict(context)
            
            # Generate SOP content using Gemini
            sop_content = await self.gemini_service.generate_sop(context_dict, template_type)
            
            # Post-process and validate
            processed_sop = self._post_process(sop_content)
            
            # Calculate metrics
            metrics = self._calculate_metrics(processed_sop)
            
            # Validate quality
            quality_check = self._validate_quality(processed_sop, metrics)
            
            return {
                "sop_content": processed_sop,
                "word_count": metrics["word_count"],
                "readability_score": metrics["readability_score"],
                "sections": metrics["sections"],
                "quality_score": quality_check["overall_score"],
                "quality_feedback": quality_check["feedback"],
                "generated_at": datetime.utcnow().isoformat(),
                "template_used": template_type,
                "context_hash": self._generate_context_hash(context),
                "meets_requirements": quality_check["meets_requirements"]
            }
            
        except Exception as e:
            logger.error(f"SOP generation failed: {str(e)}")
            raise Exception(f"Failed to generate SOP: {str(e)}")
    
    def _context_to_dict(self, context: SOPContext) -> Dict[str, Any]:
        """Convert SOPContext dataclass to dictionary."""
        return {
            'full_name': context.full_name,
            'age': context.age,
            'nationality': context.nationality,
            'current_location': context.current_location,
            'highest_qualification': context.highest_qualification,
            'institution_name': context.institution_name,
            'graduation_year': context.graduation_year,
            'gpa_percentage': context.gpa_percentage,
            'field_of_study': context.field_of_study,
            'program_name': context.program_name,
            'institution_canada': context.institution_canada,
            'program_duration': context.program_duration,
            'intake_term': context.intake_term,
            'tuition_fees': context.tuition_fees,
            'work_experience_years': context.work_experience_years,
            'current_job_title': context.current_job_title,
            'employer_name': context.employer_name,
            'relevant_experience': context.relevant_experience,
            'total_funds_available': context.total_funds_available,
            'funding_source': context.funding_source,
            'sponsor_relationship': context.sponsor_relationship,
            'career_goals': context.career_goals,
            'return_intention': context.return_intention,
            'how_program_helps': context.how_program_helps,
            'ielts_score': context.ielts_score,
            'english_proficiency': context.english_proficiency,
            'gaps_in_education': context.gaps_in_education,
            'previous_visa_refusals': context.previous_visa_refusals,
            'ties_to_home_country': context.ties_to_home_country,
            'academic_achievements': context.academic_achievements,
            'family_income': context.family_income,
            'marital_status': context.marital_status,
            'program_level': context.program_level,
            'specialization': context.specialization
        }
    
    def _validate_context(self, context: SOPContext) -> None:
        """Validate that required context fields are present."""
        required_fields = [
            'full_name', 'nationality', 'program_name', 
            'institution_canada', 'career_goals', 'total_funds_available'
        ]
        
        for field in required_fields:
            value = getattr(context, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Required field '{field}' is missing or empty")
        
        # Validate numeric fields
        if context.age <= 0 or context.age > 100:
            raise ValueError("Age must be between 1 and 100")
        
        if context.gpa_percentage < 0 or context.gpa_percentage > 100:
            raise ValueError("GPA percentage must be between 0 and 100")
        
        if context.tuition_fees <= 0:
            raise ValueError("Tuition fees must be greater than 0")
        
        if context.total_funds_available <= 0:
            raise ValueError("Total funds available must be greater than 0")
    
    def _post_process(self, content: str) -> str:
        """Post-process the generated SOP content."""
        if not content:
            raise ValueError("Generated SOP content is empty")
        
        # Clean up formatting
        lines = content.strip().split('\n')
        processed_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                processed_lines.append(line)
        
        processed_content = '\n\n'.join(processed_lines)
        
        # Ensure proper spacing and formatting
        processed_content = processed_content.replace('\n\n\n', '\n\n')
        processed_content = processed_content.replace('  ', ' ')
        
        return processed_content
    
    def _calculate_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate various metrics for the SOP."""
        if not content:
            return {"word_count": 0, "readability_score": 0, "sections": 0, "avg_sentence_length": 0}
        
        words = content.split()
        word_count = len(words)
        
        # Count sentences
        sentences = content.count('.') + content.count('!') + content.count('?')
        avg_sentence_length = word_count / max(sentences, 1)
        
        # Simple readability score (Flesch Reading Ease approximation)
        readability_score = 206.835 - (1.015 * avg_sentence_length)
        
        # Count sections (look for section headers)
        section_indicators = [
            'STATEMENT OF PURPOSE', 'ACADEMIC BACKGROUND', 'PROGRAM', 
            'CAREER', 'FINANCIAL', 'TIES TO HOME', 'CONCLUSION'
        ]
        
        sections = 0
        content_upper = content.upper()
        for indicator in section_indicators:
            if indicator in content_upper:
                sections += 1
        
        return {
            "word_count": word_count,
            "readability_score": round(readability_score, 2),
            "sections": sections,
            "avg_sentence_length": round(avg_sentence_length, 2)
        }
    
    def _validate_quality(self, content: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SOP quality against requirements."""
        feedback = []
        score_components = []
        
        # Word count validation
        word_count = metrics["word_count"]
        if word_count < settings.SOP_MIN_WORDS:
            feedback.append(f"SOP is too short ({word_count} words). Minimum required: {settings.SOP_MIN_WORDS}")
            score_components.append(50)  # Low score for insufficient length
        elif word_count > settings.SOP_MAX_WORDS:
            feedback.append(f"SOP is too long ({word_count} words). Maximum allowed: {settings.SOP_MAX_WORDS}")
            score_components.append(70)  # Moderate penalty for excessive length
        else:
            feedback.append(f"Word count is appropriate ({word_count} words)")
            score_components.append(100)
        
        # Readability validation
        readability = metrics["readability_score"]
        if readability < 30:
            feedback.append("SOP may be too complex. Consider simplifying language.")
            score_components.append(60)
        elif readability > 80:
            feedback.append("SOP may be too simple. Consider using more sophisticated language.")
            score_components.append(70)
        else:
            feedback.append("Readability is appropriate")
            score_components.append(90)
        
        # Section completeness
        sections = metrics["sections"]
        if sections < 5:
            feedback.append("SOP may be missing important sections")
            score_components.append(60)
        else:
            feedback.append("SOP contains all necessary sections")
            score_components.append(95)
        
        # Content quality checks
        content_lower = content.lower()
        
        # Check for key elements
        key_elements = [
            ('personal introduction', ['i am', 'my name is']),
            ('program mention', ['program', 'course', 'study']),
            ('career goals', ['career', 'goal', 'objective']),
            ('financial capacity', ['fund', 'financial', 'money', 'expense']),
            ('return intention', ['return', 'home country', 'back to'])
        ]
        
        element_score = 0
        for element_name, keywords in key_elements:
            if any(keyword in content_lower for keyword in keywords):
                element_score += 20
            else:
                feedback.append(f"Missing or weak {element_name}")
        
        score_components.append(element_score)
        
        # Calculate overall score
        overall_score = sum(score_components) / len(score_components)
        meets_requirements = overall_score >= 75 and word_count >= settings.SOP_MIN_WORDS
        
        return {
            "overall_score": round(overall_score, 1),
            "feedback": feedback,
            "meets_requirements": meets_requirements,
            "score_breakdown": {
                "word_count_score": score_components[0],
                "readability_score": score_components[1],
                "structure_score": score_components[2],
                "content_score": score_components[3] if len(score_components) > 3 else 0
            }
        }
    
    def _generate_context_hash(self, context: SOPContext) -> str:
        """Generate a hash for the context to track versions."""
        import hashlib
        context_str = str(context.__dict__)
        return hashlib.md5(context_str.encode()).hexdigest()[:16]
    
    async def regenerate_section(self, original_sop: str, section_name: str, 
                                context: SOPContext) -> str:
        """Regenerate a specific section of the SOP."""
        try:
            # Extract the section that needs regeneration
            context_dict = self._context_to_dict(context)
            
            # Create a focused prompt for section regeneration
            section_prompt = f"""
            Regenerate the {section_name} section of this SOP with improved content:
            
            Original SOP:
            {original_sop}
            
            Context: {context_dict}
            
            Focus on making the {section_name} section more compelling and detailed.
            """
            
            # For now, return a placeholder - in production, this would call Gemini
            return f"REGENERATED {section_name.upper()} SECTION\n\n[Enhanced content for {section_name} would be generated here using Gemini AI with the specific context and requirements.]"
            
        except Exception as e:
            logger.error(f"Section regeneration failed: {str(e)}")
            return f"Failed to regenerate {section_name} section"
    
    async def improve_sop(self, original_sop: str, feedback: str, 
                         context: SOPContext) -> str:
        """Improve SOP based on feedback."""
        try:
            context_dict = self._context_to_dict(context)
            
            improvement_prompt = f"""
            Improve this SOP based on the following feedback:
            
            Feedback: {feedback}
            
            Original SOP:
            {original_sop}
            
            Context: {context_dict}
            
            Provide an improved version that addresses the feedback while maintaining all required elements.
            """
            
            # For now, return a placeholder - in production, this would call Gemini
            return f"IMPROVED SOP\n\n[Enhanced SOP content addressing the feedback: '{feedback}' would be generated here using Gemini AI.]"
            
        except Exception as e:
            logger.error(f"SOP improvement failed: {str(e)}")
            return f"Failed to improve SOP: {str(e)}"


# Global SOP generator instance
sop_generator = SOPGenerator() 