from typing import Dict, Literal, Optional
import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import os

class SOPGenerator:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configure Gemini API
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        self.tone_styles = {
            "formal": {
                "style": "professional and academic",
                "focus": "achievements and qualifications",
                "language": "formal and precise"
            },
            "motivational": {
                "style": "inspiring and passionate",
                "focus": "personal drive and determination",
                "language": "energetic and engaging"
            },
            "personal": {
                "style": "conversational and authentic",
                "focus": "personal experiences and aspirations",
                "language": "warm and relatable"
            }
        }
        
        # Mock vector data (simulating extracted information from documents)
        self.mock_vector_data = {
            "academic_achievements": [
                "Graduated with First Class in B.Tech Computer Science",
                "Received Merit Scholarship for academic excellence",
                "Completed 3 major projects in Data Science"
            ],
            "work_experience": [
                "1 year as Data Analyst at TechCorp",
                "Led a team of 3 junior analysts",
                "Implemented data-driven solutions saving 20% costs"
            ],
            "skills": [
                "Python, R, SQL",
                "Machine Learning",
                "Data Visualization",
                "Statistical Analysis"
            ],
            "extracurricular": [
                "Technical Lead in College Coding Club",
                "Organized 2 tech workshops",
                "Participated in 3 hackathons"
            ]
        }
        
        # Load base prompt template
        self.base_prompt = """
        You are an expert SOP writer. Create a formal, well-structured, and compelling **Statement of Purpose (SOP)** for a student applying to study in Canada.

Use the following information to personalize the SOP:

Student Profile:
- Full Name: {name}
- Age: {age}
- Desired Program of Study: {program}
- Intended University: {university}

Academic Background:
{academic_background}

Work Experience:
{work_experience}

Career Goals:
- Short-Term Goals: {short_term_goals}
- Long-Term Goals: {long_term_goals}

Motivation:
- Why Study in Canada: {canada_reason}
- Why This Program: {program_reason}

Supporting Information:
- English Language Proficiency (e.g., IELTS, TOEFL): {english_score}
- Financial Support Details: {financial_support}
- Ties to Home Country (e.g., family, future job plans): {home_ties}
- Extracurricular Activities and Achievements: {extracurricular}
- Explanation of Any Gaps in Education or Employment: {gaps}

Writing Instructions:
- Tone: {tone_style} (e.g., formal, enthusiastic, confident)
- Focus: {tone_focus} (e.g., academic achievements, career planning)
- Language: {tone_language} (e.g., British English / Canadian English)

📝 **SOP Structure** (Follow this exact order):

1. **Introduction**
   - Brief self-introduction and background
   - Academic or professional status
   - Motivation and reason for pursuing higher education in Canada

2. **Academic Background**
   - Educational history
   - Key achievements, honors, and awards
   - Relevant subjects and skills developed

3. **Professional Experience**
   - Summary of work history (if applicable)
   - Key responsibilities and accomplishments
   - Skills and knowledge gained

4. **Why This Program and University**
   - Specific reasons for selecting this program
   - Relevance to previous studies or experience
   - Features of the university that influenced the choice

5. **Career Goals**
   - Clearly defined short- and long-term goals
   - How this program helps achieve those goals
   - How the Canadian education system supports the career path

6. **Ties to Home Country**
   - Social, family, or professional commitments in the home country
   - Intention to return after studies
   - Alignment of career goals with opportunities in home country

7. **Conclusion**
   - Reaffirm motivation and suitability for the program
   - Commitment to studies and returning home
   - Final statement of confidence and readiness

📏 Length: Between 800–1000 words  
📌 Requirements:
- there should not be in points, it should be in paragraphs.
- Include specific examples and accomplishments where relevant  
- Maintain a consistent {tone_style} tone throughout  
- Emphasize clear goals, strong home country ties, and genuine academic interest  

        """
    
    def generate_sop(self, 
                    data: Dict[str, str], 
                    tone: Literal["formal", "motivational", "personal"] = "formal",
                    vector_data: Optional[Dict] = None) -> str:
        """
        Generate a Statement of Purpose using Gemini API and vector data.
        
        Args:
            data: Dictionary containing student information
            tone: Writing style (formal, motivational, or personal)
            vector_data: Optional dictionary containing vector embeddings data
            
        Returns:
            str: Generated Statement of Purpose
        """
        try:
            # Use provided vector data or fall back to mock data
            vector_data = vector_data or self.mock_vector_data
            
            # Get tone instructions
            tone_info = self.tone_styles.get(tone, self.tone_styles["formal"])
            
            # Format the prompt with all required information
            prompt = self.base_prompt.format(
                name=data.get("name", ""),
                age=data.get("age", ""),
                program=data.get("program", ""),
                university=data.get("university", ""),
                academic_background=data.get("academic_background", ""),
                work_experience=data.get("work_experience", ""),
                short_term_goals=data.get("short_term_goals", ""),
                long_term_goals=data.get("long_term_goals", ""),
                canada_reason=data.get("canada_reason", ""),
                program_reason=data.get("program_reason", ""),
                english_score=data.get("english_score", ""),
                financial_support=data.get("financial_support", ""),
                home_ties=data.get("home_ties", ""),
                extracurricular=data.get("extracurricular", ""),
                gaps=data.get("gaps", ""),
                tone_style=tone_info["style"],
                tone_focus=tone_info["focus"],
                tone_language=tone_info["language"]
            )
            
            # Add vector data insights to the prompt
            prompt += "\n\nAdditional Insights from Document Analysis:\n"
            prompt += f"Academic Achievements: {', '.join(vector_data['academic_achievements'])}\n"
            prompt += f"Work Experience Highlights: {', '.join(vector_data['work_experience'])}\n"
            prompt += f"Key Skills: {', '.join(vector_data['skills'])}\n"
            prompt += f"Extracurricular Activities: {', '.join(vector_data['extracurricular'])}\n"
            
            # Generate SOP using Gemini
            response = self.model.generate_content(prompt)
            
            # Extract the generated text
            sop_text = response.text
            
            # Add header and signature
            current_year = datetime.now().year
            formatted_sop = f"""STATEMENT OF PURPOSE

{sop_text}

Sincerely,
{data.get('name', '')}
{current_year}
"""
            return formatted_sop
            
        except Exception as e:
            print(f"Error generating SOP: {str(e)}")
            return self._generate_fallback_sop(data, tone)
    
    def _generate_fallback_sop(self, data: Dict[str, str], tone: str) -> str:
        """Generate a fallback SOP if the API call fails."""
        current_year = datetime.now().year
        
        return f"""STATEMENT OF PURPOSE

Dear Admissions Committee,

I am writing to express my strong interest in the {data.get('program', '')} program at {data.get('university', 'your esteemed university')}. My name is {data.get('name', '')}, and I am excited to share my academic journey and aspirations with you.

ACADEMIC BACKGROUND
{data.get('academic_background', '')}

PROFESSIONAL EXPERIENCE
{data.get('work_experience', '')}

WHY THIS PROGRAM
{data.get('program_reason', '')}

CAREER GOALS
Short-term: {data.get('short_term_goals', '')}
Long-term: {data.get('long_term_goals', '')}

TIES TO HOME COUNTRY
{data.get('home_ties', '')}

CONCLUSION
I am confident that my academic background, professional experience, and clear career objectives make me a strong candidate for your program. I look forward to the opportunity to contribute to and learn from your academic community.

Thank you for considering my application.

Sincerely,
{data.get('name', '')}
{current_year}
"""
    
    def save_sop(self, sop_text: str, output_path: str) -> None:
        """
        Save the generated SOP to a file.
        
        Args:
            sop_text: The generated SOP text
            output_path: Path where to save the SOP
        """
        output_file = Path(output_path)
        output_file.write_text(sop_text)
