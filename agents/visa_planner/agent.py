from typing import Dict, List, Optional
from enum import Enum

class DocumentType(Enum):
    PASSPORT = "passport"
    IELTS = "ielts"
    MARKSHEETS = "marksheets"
    DEGREE = "degree"
    TRANSCRIPTS = "transcripts"
    SOP = "sop"
    LOR = "lor"
    BANK_STATEMENT = "bank_statement"

class VisaPlanner:
    def __init__(self):
        self.required_documents = {
            "UG": [
                DocumentType.PASSPORT,
                DocumentType.IELTS,
                DocumentType.MARKSHEETS,
                DocumentType.SOP,
                DocumentType.BANK_STATEMENT
            ],
            "PG": [
                DocumentType.PASSPORT,
                DocumentType.IELTS,
                DocumentType.DEGREE,
                DocumentType.TRANSCRIPTS,
                DocumentType.SOP,
                DocumentType.LOR,
                DocumentType.BANK_STATEMENT
            ]
        }
        
        self.next_steps = {
            "profile_incomplete": "Complete your profile information",
            "documents_missing": "Upload required documents",
            "sop_needed": "Generate Statement of Purpose",
            "application_ready": "Review and submit your application",
            "payment_pending": "Complete the payment process"
        }
    
    def get_next_step(self, profile_data: Dict) -> Dict:
        """
        Determine the next step in the visa application process.
        
        Args:
            profile_data: Dictionary containing profile information and uploaded documents
            
        Returns:
            Dict containing next step information and status
        """
        # Check if profile is complete
        if not self._is_profile_complete(profile_data):
            return {
                "status": "profile_incomplete",
                "next_step": self.next_steps["profile_incomplete"],
                "details": "Please complete your profile information"
            }
        
        # Get program type
        program_type = profile_data.get("program_type", "PG")
        
        # Check for missing documents
        missing_docs = self._get_missing_documents(profile_data, program_type)
        if missing_docs:
            return {
                "status": "documents_missing",
                "next_step": self.next_steps["documents_missing"],
                "details": f"Please upload: {', '.join(missing_docs)}"
            }
        
        # Check if SOP is needed
        if not profile_data.get("sop_generated"):
            return {
                "status": "sop_needed",
                "next_step": self.next_steps["sop_needed"],
                "details": "Generate your Statement of Purpose"
            }
        
        # Check payment status
        if not profile_data.get("payment_completed"):
            return {
                "status": "payment_pending",
                "next_step": self.next_steps["payment_pending"],
                "details": "Complete the payment process"
            }
        
        # All steps completed
        return {
            "status": "application_ready",
            "next_step": self.next_steps["application_ready"],
            "details": "Your application is ready for submission"
        }
    
    def _is_profile_complete(self, profile_data: Dict) -> bool:
        """Check if all required profile fields are filled."""
        required_fields = ["name", "email", "phone", "program_type", "target_university"]
        return all(field in profile_data for field in required_fields)
    
    def _get_missing_documents(self, profile_data: Dict, program_type: str) -> List[str]:
        """Get list of missing required documents."""
        uploaded_docs = set(profile_data.get("uploaded_documents", []))
        required_docs = set(doc.value for doc in self.required_documents[program_type])
        return [doc for doc in required_docs if doc not in uploaded_docs]
