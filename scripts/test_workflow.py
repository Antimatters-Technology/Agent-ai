import sys
import traceback
import os
from agents.sop_generator.agent import SOPGenerator
from agents.visa_planner.agent import VisaPlanner
from agents.checklist_generator.generator import ChecklistGenerator, ProgramType
from datetime import datetime

def main():
    try:
        print("Starting workflow test...")
        
        # Create output directory if it doesn't exist
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize agents
        print("Initializing agents...")
        sop_generator = SOPGenerator()
        visa_planner = VisaPlanner()
        checklist_generator = ChecklistGenerator()
        print("Agents initialized successfully")
        
        # Sample student data with all required fields
        student_data = {
            "name": "Rahul Sharma",
            "age": "24",
            "program": "Masters in Data Science",
            "university": "University of British Columbia",
            "academic_background": """
                - B.Tech in Computer Science (2018-2022)
                - CGPA: 8.5/10
                - University: Delhi Technological University
                - Relevant Courses: Data Structures, Machine Learning, Statistics
            """,
            "work_experience": """
                - Data Analyst at TechCorp (2022-Present)
                - Responsibilities: Data analysis, ML model development
                - Achievements: Implemented cost-saving solutions
            """,
            "short_term_goals": "Gain expertise in AI and Machine Learning",
            "long_term_goals": "Become a Data Science Lead and contribute to AI research",
            "canada_reason": "World-class education and research opportunities in AI",
            "program_reason": "Strong focus on practical applications and industry connections",
            "english_score": "IELTS 7.5 (L:8, R:7.5, W:7, S:7.5)",
            "financial_support": "Self-funded with support from parents",
            "home_ties": "Family business in India, property ownership",
            "extracurricular": "Technical lead in college coding club, hackathon winner",
            "gaps": "None"
        }
        
        print("\n=== VisaMate-AI Workflow Demo ===\n")
        
        # 1. Generate SOP
        print("1. Generating Statement of Purpose...")
        sop = sop_generator.generate_sop(student_data, tone="motivational")
        
        # Save SOP to file
        sop_filename = f"{output_dir}/sop_{student_data['name'].lower().replace(' ', '_')}.txt"
        sop_generator.save_sop(sop, sop_filename)
        
        print(f"\nGenerated SOP has been saved to: {sop_filename}")
        print("\nFull SOP Content:")
        print("=" * 80)
        print(sop)
        print("=" * 80)
        print()
        
        # 2. Get next steps
        print("2. Checking application status...")
        profile_data = {
            **student_data,
            "uploaded_documents": ["passport", "ielts"],
            "sop_generated": True,
            "payment_completed": False
        }
        next_step = visa_planner.get_next_step(profile_data)
        print(f"Status: {next_step['status']}")
        print(f"Next Step: {next_step['next_step']}")
        print(f"Details: {next_step['details']}\n")
        
        # 3. Generate checklist
        print("3. Generating document checklist...")
        uploaded_docs = {
            "passport": {
                "uploaded_at": datetime.now().isoformat(),
                "file_url": "https://example.com/passport.pdf"
            },
            "ielts": {
                "uploaded_at": datetime.now().isoformat(),
                "file_url": "https://example.com/ielts.pdf"
            }
        }
        checklist = checklist_generator.generate_checklist(ProgramType.PG, uploaded_docs)
        status = checklist_generator.get_checklist_status(checklist)
        
        print("\nRequired Documents:")
        for item in checklist:
            print(f"- {item['name']}: {item['status']}")
        
        print(f"\nOverall Progress: {status['completion_percentage']:.1f}%")
        print(f"Required Documents Complete: {status['completed_required']}/{status['required_items']}")
        
        print("\nWorkflow test completed successfully!")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 