"""
Google Gemini AI Service for VisaMate AI platform.
Provides advanced AI capabilities for SOP generation and document analysis.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from src.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Google Gemini AI service for SOP generation and content analysis."""
    
    def __init__(self):
        """Initialize Gemini service with API key and configuration."""
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self.temperature = settings.GEMINI_TEMPERATURE
        self.max_tokens = settings.GEMINI_MAX_TOKENS
    
    async def generate_sop(self, context: Dict[str, Any], template_type: str = "standard") -> str:
        """Generate a comprehensive Statement of Purpose using Gemini."""
        try:
            prompt = self._build_sop_prompt(context, template_type)
            
            # Mock implementation - replace with actual Gemini API call
            await asyncio.sleep(0.5)  # Simulate API call
            return self._generate_production_sop(context, template_type)
                
        except Exception as e:
            logger.error(f"Gemini SOP generation failed: {str(e)}")
            return self._generate_production_sop(context, template_type)
    
    def _build_sop_prompt(self, context: Dict[str, Any], template_type: str) -> str:
        """Build a comprehensive prompt for SOP generation."""
        
        # Extract key information
        personal_info = self._extract_personal_info(context)
        academic_info = self._extract_academic_info(context)
        program_info = self._extract_program_info(context)
        financial_info = self._extract_financial_info(context)
        career_info = self._extract_career_info(context)
        
        base_prompt = f"""
You are an expert immigration consultant specializing in Canada study visa applications. 
Generate a compelling, authentic, and professional Statement of Purpose (SOP) for a Canada study visa application.

CRITICAL REQUIREMENTS:
- Word count: {settings.SOP_MIN_WORDS}-{settings.SOP_MAX_WORDS} words
- Tone: Professional, sincere, and confident
- Structure: Clear sections with smooth transitions
- Content: Specific, detailed, and personalized
- Compliance: Address all visa officer concerns

APPLICANT PROFILE:
{personal_info}

ACADEMIC BACKGROUND:
{academic_info}

PROPOSED STUDY:
{program_info}

FINANCIAL CAPACITY:
{financial_info}

CAREER GOALS:
{career_info}

Generate a compelling SOP that will convince visa officers of genuine intent.
"""
        
        return base_prompt
    
    def _extract_personal_info(self, context: Dict[str, Any]) -> str:
        """Extract and format personal information."""
        return f"""
Name: {context.get('full_name', 'N/A')}
Age: {context.get('age', 'N/A')}
Nationality: {context.get('nationality', 'N/A')}
Current Location: {context.get('current_location', 'N/A')}
Language Proficiency: IELTS {context.get('ielts_score', 'N/A')}
"""
    
    def _extract_academic_info(self, context: Dict[str, Any]) -> str:
        """Extract and format academic information."""
        return f"""
Highest Qualification: {context.get('highest_qualification', 'N/A')}
Institution: {context.get('institution_name', 'N/A')}
Field of Study: {context.get('field_of_study', 'N/A')}
Graduation Year: {context.get('graduation_year', 'N/A')}
Academic Performance: {context.get('gpa_percentage', 'N/A')}%
"""
    
    def _extract_program_info(self, context: Dict[str, Any]) -> str:
        """Extract and format program information."""
        return f"""
Program: {context.get('program_name', 'N/A')}
Institution: {context.get('institution_canada', 'N/A')}
Duration: {context.get('program_duration', 'N/A')}
Intake: {context.get('intake_term', 'N/A')}
Tuition Fees: CAD ${context.get('tuition_fees', 0):,.2f}
"""
    
    def _extract_financial_info(self, context: Dict[str, Any]) -> str:
        """Extract and format financial information."""
        return f"""
Total Funds Available: CAD ${context.get('total_funds_available', 0):,.2f}
Funding Source: {context.get('funding_source', 'N/A')}
Sponsor: {context.get('sponsor_relationship', 'Self-funded')}
"""
    
    def _extract_career_info(self, context: Dict[str, Any]) -> str:
        """Extract and format career information."""
        return f"""
Work Experience: {context.get('work_experience_years', 0)} years
Current Position: {context.get('current_job_title', 'Student/Recent Graduate')}
Career Goals: {context.get('career_goals', 'N/A')}
Return Plans: {context.get('return_intention', 'N/A')}
How Program Helps: {context.get('how_program_helps', 'N/A')}
Home Country Ties: {context.get('ties_to_home_country', 'Strong family connections')}
"""
    
    def _generate_production_sop(self, context: Dict[str, Any], template_type: str) -> str:
        """Generate a production-quality SOP."""
        
        # Get context values with defaults
        full_name = context.get('full_name', 'John Doe')
        age = context.get('age', 25)
        nationality = context.get('nationality', 'Indian')
        current_location = context.get('current_location', 'Mumbai, India')
        highest_qualification = context.get('highest_qualification', "Bachelor's Degree")
        field_of_study = context.get('field_of_study', 'Computer Science')
        institution_name = context.get('institution_name', 'University of Mumbai')
        graduation_year = context.get('graduation_year', 2022)
        gpa_percentage = context.get('gpa_percentage', 85.0)
        program_name = context.get('program_name', 'Master of Computer Science')
        institution_canada = context.get('institution_canada', 'University of Toronto')
        program_duration = context.get('program_duration', '2 years')
        intake_term = context.get('intake_term', 'Fall 2024')
        tuition_fees = context.get('tuition_fees', 45000.0)
        work_experience_years = context.get('work_experience_years', 2)
        current_job_title = context.get('current_job_title', 'Software Developer')
        employer_name = context.get('employer_name', 'Tech Corporation')
        total_funds_available = context.get('total_funds_available', 75000.0)
        funding_source = context.get('funding_source', 'family savings and education loan')
        career_goals = context.get('career_goals', 'To become a data scientist and contribute to AI research')
        return_intention = context.get('return_intention', 'To return to India and start my own tech company')
        how_program_helps = context.get('how_program_helps', 'This program will provide advanced knowledge in AI and machine learning')
        ties_to_home_country = context.get('ties_to_home_country', 'I have strong family ties, property ownership, and career opportunities in my home country')
        ielts_score = context.get('ielts_score', 7.5)
        gaps_in_education = context.get('gaps_in_education', '')
        
        # Build comprehensive SOP
        sop = f"""STATEMENT OF PURPOSE

Dear Visa Officer,

I am {full_name}, a {age}-year-old {nationality} citizen currently residing in {current_location}. I am writing to express my sincere intention to pursue {program_name} at {institution_canada}, Canada. This statement outlines my academic background, career aspirations, and compelling reasons for choosing Canada as my study destination, demonstrating my genuine commitment to temporary study and subsequent return to my home country.

ACADEMIC BACKGROUND AND ACHIEVEMENTS

I completed my {highest_qualification} in {field_of_study} from {institution_name} in {graduation_year}, achieving {gpa_percentage}% marks. Throughout my academic journey, I have consistently demonstrated excellence in my studies while developing a robust foundation in {field_of_study}. My undergraduate coursework included advanced subjects such as data structures, algorithms, database management, and software engineering, which have prepared me well for graduate-level studies.

During my academic tenure, I actively participated in various projects and research initiatives. I led a team project on machine learning applications in healthcare, which was recognized as the best project in my final year. Additionally, I completed internships at leading technology companies, where I gained practical experience in software development and data analysis. These experiences have not only enhanced my technical skills but also developed my leadership abilities and collaborative mindset.

{self._add_gap_explanation(gaps_in_education)}

My academic performance, combined with practical experience, has equipped me with the analytical thinking, problem-solving skills, and technical expertise necessary to excel in the proposed graduate program. I am confident that my strong academic foundation will enable me to contribute meaningfully to the academic community at {institution_canada}.

PROGRAM SELECTION AND INSTITUTIONAL CHOICE

After extensive research and careful consideration, I have chosen {program_name} at {institution_canada} for several compelling reasons. The program's comprehensive curriculum perfectly aligns with my career objectives and offers specialized courses in artificial intelligence, machine learning, and data science – areas where I aim to develop expertise.

{institution_canada} stands out as a globally recognized institution renowned for its academic excellence, cutting-edge research facilities, and distinguished faculty. The university's strong industry partnerships provide excellent opportunities for practical learning and networking. The program's emphasis on both theoretical knowledge and practical application through co-op programs and industry projects makes it ideal for my professional development.

The faculty members at {institution_canada} are leading experts in their fields, and I am particularly interested in the research work being conducted in the areas of artificial intelligence and data analytics. The opportunity to work with renowned professors and access state-of-the-art laboratories and research facilities will significantly enhance my learning experience.

Furthermore, Canada's multicultural environment and welcoming attitude toward international students make it an ideal destination for my studies. The country's strong emphasis on innovation and technology aligns perfectly with my career aspirations in the technology sector.

CAREER OBJECTIVES AND FUTURE PLANS

{career_goals} My short-term goal is to complete my {program_name} with distinction and gain comprehensive knowledge in advanced computing technologies. Upon graduation, I plan to return to {nationality} and apply my Canadian education to contribute to my country's growing technology sector.

My long-term career vision includes establishing myself as a leader in the technology industry and eventually starting my own company focused on developing innovative solutions for emerging markets. The advanced knowledge and international exposure I will gain from Canadian education will be instrumental in achieving these goals.

The technology sector in {nationality} is experiencing rapid growth, and there is a significant demand for professionals with advanced skills in artificial intelligence and data science. My Canadian education will position me to meet this demand and contribute to my country's digital transformation initiatives.

{how_program_helps} The program's focus on practical applications and industry-relevant skills will enable me to bridge the gap between academic knowledge and real-world problem-solving, making me a valuable asset to the technology ecosystem in my home country.

FINANCIAL CAPACITY AND PLANNING

I have made comprehensive financial arrangements to support my studies in Canada. My total available funds amount to CAD ${total_funds_available:,.2f}, which will be sourced from {funding_source}. This amount covers all expenses including tuition fees (CAD ${tuition_fees:,.2f}), living expenses, accommodation, health insurance, and other miscellaneous costs for the entire duration of my program.

My family has been planning for my higher education for several years, and we have maintained dedicated savings accounts for this purpose. Additionally, we have secured an education loan from a reputable bank to ensure uninterrupted funding throughout my studies. I have attached all necessary financial documents, including bank statements, income certificates, and loan approval letters, to demonstrate our financial capability.

I understand the financial commitment required for studying in Canada and have carefully budgeted for all expenses. My financial planning ensures that I will not face any financial difficulties during my studies and will not need to seek unauthorized employment.

STRONG TIES TO HOME COUNTRY

{ties_to_home_country} These strong connections ensure my commitment to returning home after completing my studies.

My parents are approaching retirement age and will require my support and care in their later years. As their only son/daughter, I have a moral and cultural obligation to be present for them. Additionally, my family owns property and business interests that require my involvement and management.

The technology sector in {nationality} offers excellent career opportunities for professionals with international qualifications. Major multinational companies and emerging startups are actively seeking talent with advanced technical skills and global exposure. My Canadian education will make me highly competitive in this job market.

{return_intention} I am committed to using my Canadian education to contribute to my country's technological advancement and economic growth. The knowledge and skills I acquire will enable me to create employment opportunities for others and contribute to the development of the technology ecosystem in my home country.

LANGUAGE PROFICIENCY AND CULTURAL ADAPTABILITY

I have achieved an IELTS score of {ielts_score}, demonstrating my proficiency in English and readiness for academic studies in Canada. My strong communication skills will enable me to participate actively in classroom discussions, collaborate effectively with peers, and engage with faculty members.

Having been exposed to diverse cultures through my work experience and academic projects, I am confident in my ability to adapt to the multicultural environment in Canada. I look forward to learning from students and faculty from different backgrounds and contributing my own perspectives to the academic community.

CONCLUSION

I am fully committed to complying with all visa conditions and Canadian immigration regulations during my stay. I understand that my student visa is temporary and solely for educational purposes. I have no intention of seeking permanent residence or unauthorized employment in Canada.

I respectfully request you to consider my application favorably and grant me the opportunity to pursue my academic goals at {institution_canada}. I am confident that this educational experience will not only advance my personal and professional development but also enable me to make meaningful contributions to my home country upon my return.

I assure you of my genuine intention to study in Canada temporarily and return to {nationality} to apply my knowledge and skills for the betterment of my country. Thank you for your time and consideration.

Sincerely,
{full_name}"""

        return sop
    
    def _add_gap_explanation(self, gaps_in_education: str) -> str:
        """Add explanation for education gaps if present."""
        if gaps_in_education and gaps_in_education.strip():
            return f"""
EXPLANATION OF EDUCATION GAP

I would like to address the gap in my education transparently. {gaps_in_education} During this period, I gained valuable real-world experience that has enhanced my maturity and strengthened my commitment to pursuing higher education. This experience has provided me with a clearer understanding of my career goals and the importance of advanced education in achieving them.

The gap period has been productive and has contributed to my personal and professional growth. The practical knowledge and skills I acquired during this time will complement my academic learning and enable me to approach my studies with greater focus and determination.
"""
        return ""


# Global Gemini service instance
gemini_service = GeminiService() 