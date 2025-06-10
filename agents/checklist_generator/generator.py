from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class ProgramType(Enum):
    UG = "undergraduate"
    PG = "postgraduate"
    PHD = "phd"

@dataclass
class ChecklistItem:
    id: str
    name: str
    description: str
    is_required: bool
    status: str = "pending"
    uploaded_at: Optional[datetime] = None
    file_url: Optional[str] = None

class ChecklistGenerator:
    def __init__(self):
        self.base_checklist = {
            ProgramType.UG: [
                ChecklistItem(
                    id="passport",
                    name="Passport",
                    description="Valid passport with at least 6 months validity",
                    is_required=True
                ),
                ChecklistItem(
                    id="ielts",
                    name="IELTS Score",
                    description="IELTS score of 6.0 or above",
                    is_required=True
                ),
                ChecklistItem(
                    id="marksheets",
                    name="10+2 Marksheets",
                    description="Original marksheets from 10th and 12th grade",
                    is_required=True
                ),
                ChecklistItem(
                    id="sop",
                    name="Statement of Purpose",
                    description="Personal statement explaining your goals and motivation",
                    is_required=True
                ),
                ChecklistItem(
                    id="bank_statement",
                    name="Bank Statement",
                    description="Proof of sufficient funds for study and living expenses",
                    is_required=True
                )
            ],
            ProgramType.PG: [
                ChecklistItem(
                    id="passport",
                    name="Passport",
                    description="Valid passport with at least 6 months validity",
                    is_required=True
                ),
                ChecklistItem(
                    id="ielts",
                    name="IELTS Score",
                    description="IELTS score of 6.5 or above",
                    is_required=True
                ),
                ChecklistItem(
                    id="degree",
                    name="Bachelor's Degree",
                    description="Original degree certificate",
                    is_required=True
                ),
                ChecklistItem(
                    id="transcripts",
                    name="Academic Transcripts",
                    description="Detailed transcripts from undergraduate studies",
                    is_required=True
                ),
                ChecklistItem(
                    id="sop",
                    name="Statement of Purpose",
                    description="Personal statement explaining your goals and motivation",
                    is_required=True
                ),
                ChecklistItem(
                    id="lor",
                    name="Letters of Recommendation",
                    description="Two academic or professional letters of recommendation",
                    is_required=True
                ),
                ChecklistItem(
                    id="bank_statement",
                    name="Bank Statement",
                    description="Proof of sufficient funds for study and living expenses",
                    is_required=True
                )
            ]
        }
    
    def generate_checklist(self, 
                          program_type: ProgramType,
                          uploaded_docs: Optional[Dict[str, Dict]] = None) -> List[Dict]:
        """
        Generate a checklist based on program type and update status of uploaded documents.
        
        Args:
            program_type: Type of program (UG/PG)
            uploaded_docs: Dictionary of uploaded documents with their details
            
        Returns:
            List of checklist items with their status
        """
        # Get base checklist for program type
        checklist = self.base_checklist.get(program_type, [])
        
        # Update status of uploaded documents
        if uploaded_docs:
            for item in checklist:
                if item.id in uploaded_docs:
                    doc_info = uploaded_docs[item.id]
                    item.status = "completed"
                    item.uploaded_at = datetime.fromisoformat(doc_info.get("uploaded_at"))
                    item.file_url = doc_info.get("file_url")
        
        # Convert to dictionary format for API response
        return [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "is_required": item.is_required,
                "status": item.status,
                "uploaded_at": item.uploaded_at.isoformat() if item.uploaded_at else None,
                "file_url": item.file_url
            }
            for item in checklist
        ]
    
    def get_checklist_status(self, checklist: List[Dict]) -> Dict:
        """
        Get overall status of the checklist.
        
        Args:
            checklist: List of checklist items
            
        Returns:
            Dictionary containing status summary
        """
        total_items = len(checklist)
        completed_items = sum(1 for item in checklist if item["status"] == "completed")
        required_items = sum(1 for item in checklist if item["is_required"])
        completed_required = sum(1 for item in checklist 
                               if item["is_required"] and item["status"] == "completed")
        
        return {
            "total_items": total_items,
            "completed_items": completed_items,
            "required_items": required_items,
            "completed_required": completed_required,
            "completion_percentage": (completed_items / total_items) * 100 if total_items > 0 else 0,
            "is_complete": completed_required == required_items
        }
