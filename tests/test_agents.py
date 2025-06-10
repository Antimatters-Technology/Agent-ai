import pytest
from datetime import datetime
from agents.sop_generator.agent import SOPGenerator
from agents.visa_planner.agent import VisaPlanner, DocumentType
from agents.checklist_generator.generator import ChecklistGenerator, ProgramType

def test_sop_generator():
    generator = SOPGenerator()
    
    # Test data
    data = {
        "name": "John Doe",
        "program": "Masters in Computer Science",
        "background": "Bachelor's in IT with 2 years of experience",
        "goals": "Become a software architect"
    }
    
    # Test different tones
    for tone in ["formal", "motivational", "personal"]:
        sop = generator.generate_sop(data, tone)
        assert isinstance(sop, str)
        assert data["name"] in sop
        assert data["program"] in sop

def test_visa_planner():
    planner = VisaPlanner()
    
    # Test incomplete profile
    incomplete_profile = {
        "name": "John Doe",
        "email": "john@example.com"
    }
    next_step = planner.get_next_step(incomplete_profile)
    assert next_step["status"] == "profile_incomplete"
    
    # Test missing documents
    profile_with_docs = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "1234567890",
        "program_type": "PG",
        "target_university": "University of Toronto",
        "uploaded_documents": ["passport"]
    }
    next_step = planner.get_next_step(profile_with_docs)
    assert next_step["status"] == "documents_missing"
    
    # Test complete profile
    complete_profile = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "1234567890",
        "program_type": "PG",
        "target_university": "University of Toronto",
        "uploaded_documents": [doc.value for doc in planner.required_documents["PG"]],
        "sop_generated": True,
        "payment_completed": True
    }
    next_step = planner.get_next_step(complete_profile)
    assert next_step["status"] == "application_ready"

def test_checklist_generator():
    generator = ChecklistGenerator()
    
    # Test UG checklist
    ug_checklist = generator.generate_checklist(ProgramType.UG)
    assert len(ug_checklist) > 0
    assert any(item["id"] == "passport" for item in ug_checklist)
    
    # Test PG checklist
    pg_checklist = generator.generate_checklist(ProgramType.PG)
    assert len(pg_checklist) > 0
    assert any(item["id"] == "lor" for item in pg_checklist)
    
    # Test with uploaded documents
    uploaded_docs = {
        "passport": {
            "uploaded_at": datetime.now().isoformat(),
            "file_url": "https://example.com/passport.pdf"
        }
    }
    checklist_with_uploads = generator.generate_checklist(ProgramType.UG, uploaded_docs)
    passport_item = next(item for item in checklist_with_uploads if item["id"] == "passport")
    assert passport_item["status"] == "completed"
    assert passport_item["file_url"] is not None
    
    # Test checklist status
    status = generator.get_checklist_status(checklist_with_uploads)
    assert "completion_percentage" in status
    assert "is_complete" in status
    assert isinstance(status["completion_percentage"], float)
    assert isinstance(status["is_complete"], bool) 