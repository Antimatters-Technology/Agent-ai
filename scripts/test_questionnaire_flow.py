#!/usr/bin/env python3
"""
Test script for IRCC Questionnaire Flow and Document Processing.
Validates the complete Canada Study Visa application workflow.
"""

import asyncio
import json
import logging
from datetime import date, datetime
from typing import Dict, Any

import httpx
from pydantic import ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/wizard"


class QuestionnaireFlowTester:
    """Test class for IRCC questionnaire flow."""
    
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.session_id = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def create_sample_questionnaire_responses(self) -> Dict[str, Any]:
        """Create sample questionnaire responses based on the provided data."""
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
            "has_valid_permits": False,
            "is_exchange_student": False,
            "work_essential_to_studies": False,
            "has_family_in_canada": False,
            "has_scholarship": False,
            "criminal_background": False,
            "wants_family_application": False,
            "giving_access_to_application": False,
            "has_biometrics": False,
            "will_pay_fees": True,
            "can_scan_documents": True,
            "pay_online": True
        }
    
    async def test_start_wizard_session(self) -> bool:
        """Test starting a new wizard session."""
        logger.info("Testing wizard session start...")
        
        try:
            response = await self.client.post(f"{API_BASE}/start?user_id=test_user")
            
            if response.status_code == 200:
                data = response.json()
                self.session_id = data["session_id"]
                logger.info(f"✅ Session started successfully: {self.session_id}")
                logger.info(f"   Current step: {data['current_step']}")
                logger.info(f"   Document checklist items: {len(data['document_checklist']['application_forms']) + len(data['document_checklist']['supporting_documents'])}")
                return True
            else:
                logger.error(f"❌ Failed to start session: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during session start: {str(e)}")
            return False
    
    async def test_submit_questionnaire(self) -> bool:
        """Test submitting questionnaire responses."""
        logger.info("Testing questionnaire submission...")
        
        if not self.session_id:
            logger.error("❌ No session ID available")
            return False
        
        try:
            questionnaire_data = {
                "responses": self.create_sample_questionnaire_responses()
            }
            
            response = await self.client.post(
                f"{API_BASE}/questionnaire/{self.session_id}",
                json=questionnaire_data
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Questionnaire submitted successfully")
                logger.info(f"   Updated step: {data['current_step']}")
                logger.info(f"   Forms prefilled: {data['forms_prefilled']}")
                return True
            else:
                logger.error(f"❌ Failed to submit questionnaire: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during questionnaire submission: {str(e)}")
            return False
    
    async def test_generate_sop(self) -> bool:
        """Test SOP generation from questionnaire."""
        logger.info("Testing SOP generation...")
        
        if not self.session_id:
            logger.error("❌ No session ID available")
            return False
        
        try:
            response = await self.client.post(f"{API_BASE}/generate-sop/{self.session_id}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ SOP generated successfully")
                logger.info(f"   Word count: {data['word_count']}")
                logger.info(f"   Quality score: {data['quality_score']}")
                logger.info(f"   Meets requirements: {data['meets_requirements']}")
                logger.info(f"   SOP preview: {data['sop_content'][:200]}...")
                return True
            else:
                logger.error(f"❌ Failed to generate SOP: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during SOP generation: {str(e)}")
            return False
    
    async def test_get_document_checklist(self) -> bool:
        """Test getting document checklist."""
        logger.info("Testing document checklist retrieval...")
        
        if not self.session_id:
            logger.error("❌ No session ID available")
            return False
        
        try:
            response = await self.client.get(f"{API_BASE}/document-checklist/{self.session_id}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Document checklist retrieved successfully")
                
                # Count documents
                app_forms = len(data["application_forms"])
                supporting = len(data["supporting_documents"])
                optional = len(data["optional_documents"])
                
                logger.info(f"   Application forms: {app_forms}")
                logger.info(f"   Supporting documents: {supporting}")
                logger.info(f"   Optional documents: {optional}")
                logger.info(f"   Total fee: CAD ${data['total_fee_cad']}")
                
                # List required documents
                logger.info("   Required documents:")
                for doc in data["supporting_documents"]:
                    if doc["is_required"]:
                        logger.info(f"     - {doc['document_name']}")
                
                return True
            else:
                logger.error(f"❌ Failed to get document checklist: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during document checklist retrieval: {str(e)}")
            return False
    
    async def test_get_prefilled_forms(self) -> bool:
        """Test getting prefilled forms."""
        logger.info("Testing prefilled forms retrieval...")
        
        if not self.session_id:
            logger.error("❌ No session ID available")
            return False
        
        try:
            response = await self.client.get(f"{API_BASE}/prefilled-forms/{self.session_id}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Prefilled forms retrieved successfully")
                logger.info(f"   Available forms: {list(data['forms'].keys())}")
                return True
            else:
                logger.error(f"❌ Failed to get prefilled forms: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during prefilled forms retrieval: {str(e)}")
            return False
    
    async def test_document_upload(self) -> bool:
        """Test document upload functionality."""
        logger.info("Testing document upload...")
        
        if not self.session_id:
            logger.error("❌ No session ID available")
            return False
        
        try:
            # Simulate a document upload
            upload_data = {
                "document_type": "passport",
                "file_name": "passport.pdf",
                "file_content": "base64_encoded_content_here"
            }
            
            response = await self.client.post(
                f"{API_BASE}/upload-document/{self.session_id}",
                json=upload_data
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Document uploaded successfully")
                logger.info(f"   Document type: {data['document_type']}")
                logger.info(f"   File name: {data['file_name']}")
                return True
            else:
                logger.error(f"❌ Failed to upload document: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during document upload: {str(e)}")
            return False
    
    async def test_health_check(self) -> bool:
        """Test application health check."""
        logger.info("Testing application health...")
        
        try:
            response = await self.client.get(f"{BASE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ Application health check passed")
                logger.info(f"   Status: {data['status']}")
                logger.info(f"   Environment: {data['environment']}")
                return True
            else:
                logger.error(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception during health check: {str(e)}")
            return False
    
    async def run_complete_flow_test(self) -> Dict[str, bool]:
        """Run the complete questionnaire flow test."""
        logger.info("🚀 Starting complete IRCC questionnaire flow test...")
        logger.info("=" * 60)
        
        results = {}
        
        # Test sequence
        test_sequence = [
            ("Health Check", self.test_health_check),
            ("Start Wizard Session", self.test_start_wizard_session),
            ("Submit Questionnaire", self.test_submit_questionnaire),
            ("Generate SOP", self.test_generate_sop),
            ("Get Document Checklist", self.test_get_document_checklist),
            ("Get Prefilled Forms", self.test_get_prefilled_forms),
            ("Upload Document", self.test_document_upload),
        ]
        
        for test_name, test_func in test_sequence:
            logger.info(f"\n📋 Running: {test_name}")
            results[test_name] = await test_func()
            
            if not results[test_name]:
                logger.warning(f"⚠️  Test '{test_name}' failed, continuing with remaining tests...")
        
        return results
    
    def print_test_summary(self, results: Dict[str, bool]):
        """Print test summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} - {test_name}")
        
        logger.info("-" * 60)
        logger.info(f"📈 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 All tests passed! The questionnaire flow is working correctly.")
        else:
            logger.warning(f"⚠️  {total - passed} test(s) failed. Please check the logs above.")


async def main():
    """Main test execution function."""
    print("🇨🇦 VisaMate AI - IRCC Questionnaire Flow Test")
    print("=" * 60)
    print("Testing the complete Canada Study Visa application workflow")
    print("=" * 60)
    
    async with QuestionnaireFlowTester() as tester:
        results = await tester.run_complete_flow_test()
        tester.print_test_summary(results)
    
    print("\n🏁 Test execution completed!")


if __name__ == "__main__":
    asyncio.run(main()) 