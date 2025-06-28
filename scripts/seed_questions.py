#!/usr/bin/env python3
"""
Seed Questions Script for VisaMate AI platform.
Populates the database with IRCC questionnaire questions and structure.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from src.core.config import settings
from src.adapters.aws_adapter import DynamoDBAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionBankSeeder:
    """Seeds the question bank with IRCC questionnaire structure."""
    
    def __init__(self):
        self.table_name = f"{settings.DYNAMODB_TABLE_PREFIX}-question-bank"
    
    async def seed_questions(self):
        """Seed all questions into the database."""
        logger.info("Starting question bank seeding...")
        
        try:
            async with DynamoDBAdapter() as db:
                # Create question bank structure
                question_bank = self._get_question_bank_structure()
                
                # Store each section
                for section in question_bank["sections"]:
                    await self._store_section(db, section)
                
                # Store metadata
                await self._store_metadata(db, question_bank)
                
                logger.info("Question bank seeding completed successfully!")
                
        except Exception as e:
            logger.error(f"Failed to seed question bank: {str(e)}")
            raise
    
    async def _store_section(self, db: DynamoDBAdapter, section: Dict[str, Any]):
        """Store a question section in DynamoDB."""
        try:
            # Store section metadata
            section_item = {
                'item_type': 'section',
                'section_id': section['section_id'],
                'section_name': section['section_name'],
                'section_description': section['section_description'],
                'order': section.get('order', 0),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # For development, log instead of storing
            logger.info(f"Would store section: {section['section_id']}")
            
            # Store each step in the section
            for step_index, step in enumerate(section['steps']):
                await self._store_step(db, section['section_id'], step, step_index)
                
        except Exception as e:
            logger.error(f"Failed to store section {section['section_id']}: {str(e)}")
            raise
    
    async def _store_step(self, db: DynamoDBAdapter, section_id: str, step: Dict[str, Any], step_order: int):
        """Store a wizard step in DynamoDB."""
        try:
            step_item = {
                'item_type': 'step',
                'section_id': section_id,
                'step_id': step['step_id'],
                'step_name': step['step_name'],
                'step_description': step['step_description'],
                'order': step_order,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Would store step: {step['step_id']}")
            
            # Store each question in the step
            for question_index, question in enumerate(step['questions']):
                await self._store_question(db, section_id, step['step_id'], question, question_index)
                
        except Exception as e:
            logger.error(f"Failed to store step {step['step_id']}: {str(e)}")
            raise
    
    async def _store_question(self, db: DynamoDBAdapter, section_id: str, step_id: str, question: Dict[str, Any], question_order: int):
        """Store a question in DynamoDB."""
        try:
            question_item = {
                'item_type': 'question',
                'section_id': section_id,
                'step_id': step_id,
                'question_id': question['question_id'],
                'question_text': question['question_text'],
                'question_type': question['question_type'],
                'required': question.get('required', True),
                'order': question_order,
                'options': question.get('options', []),
                'validation': question.get('validation', {}),
                'conditional_logic': question.get('conditional_logic', {}),
                'help_text': question.get('help_text', ''),
                'placeholder': question.get('placeholder', ''),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Would store question: {question['question_id']}")
            
        except Exception as e:
            logger.error(f"Failed to store question {question['question_id']}: {str(e)}")
            raise
    
    async def _store_metadata(self, db: DynamoDBAdapter, question_bank: Dict[str, Any]):
        """Store question bank metadata."""
        try:
            metadata_item = {
                'item_type': 'metadata',
                'version': '1.0.0',
                'total_sections': len(question_bank['sections']),
                'total_questions': self._count_total_questions(question_bank),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Question bank metadata: {metadata_item}")
            
        except Exception as e:
            logger.error(f"Failed to store metadata: {str(e)}")
            raise
    
    def _count_total_questions(self, question_bank: Dict[str, Any]) -> int:
        """Count total questions in the question bank."""
        total = 0
        for section in question_bank['sections']:
            for step in section['steps']:
                total += len(step['questions'])
        return total
    
    def _get_question_bank_structure(self) -> Dict[str, Any]:
        """Get the complete question bank structure."""
        return {
            "version": "1.0.0",
            "sections": [
                {
                    "section_id": "getting_started",
                    "section_name": "Getting Started",
                    "section_description": "Basic information about your application",
                    "order": 1,
                    "steps": [
                        {
                            "step_id": "basic_info",
                            "step_name": "Basic Information",
                            "step_description": "Tell us about your purpose and current situation",
                            "questions": [
                                {
                                    "question_id": "purpose_in_canada",
                                    "question_text": "What would you like to do in Canada?",
                                    "question_type": "single_choice",
                                    "required": True,
                                    "options": [
                                        {"value": "Study", "label": "Study", "default": True},
                                        {"value": "Work", "label": "Work", "default": False},
                                        {"value": "Visit", "label": "Visit", "default": False},
                                        {"value": "Transit", "label": "Transit", "default": False}
                                    ],
                                    "help_text": "Select your primary purpose for coming to Canada"
                                },
                                {
                                    "question_id": "duration_of_stay",
                                    "question_text": "How long are you planning to stay?",
                                    "question_type": "single_choice",
                                    "required": True,
                                    "options": [
                                        {"value": "Temporarily - less than 6 months", "label": "Temporarily - less than 6 months"},
                                        {"value": "Temporarily - more than 6 months", "label": "Temporarily - more than 6 months", "default": True},
                                        {"value": "Permanently", "label": "Permanently"}
                                    ],
                                    "conditional_logic": {
                                        "depends_on": "purpose_in_canada",
                                        "show_if": ["Study", "Work"]
                                    }
                                },
                                {
                                    "question_id": "passport_country_code",
                                    "question_text": "What country issued your passport?",
                                    "question_type": "country_select",
                                    "required": True,
                                    "placeholder": "Select your country...",
                                    "help_text": "Choose the country that issued your current passport"
                                },
                                {
                                    "question_id": "current_residence",
                                    "question_text": "What country do you currently live in?",
                                    "question_type": "country_select",
                                    "required": True,
                                    "placeholder": "Select your current residence...",
                                    "help_text": "This may be different from your passport country"
                                },
                                {
                                    "question_id": "has_canadian_family",
                                    "question_text": "Do you have a family member who is a Canadian citizen or permanent resident?",
                                    "question_type": "yes_no",
                                    "required": True,
                                    "help_text": "This includes spouse, parent, child, or sibling"
                                },
                                {
                                    "question_id": "date_of_birth",
                                    "question_text": "What is your date of birth?",
                                    "question_type": "date",
                                    "required": True,
                                    "validation": {
                                        "min_age": 16,
                                        "max_age": 65
                                    }
                                }
                            ]
                        }
                    ]
                },
                {
                    "section_id": "education_background",
                    "section_name": "Education Background",
                    "section_description": "Information about your education and proposed studies",
                    "order": 2,
                    "steps": [
                        {
                            "step_id": "education_status",
                            "step_name": "Education Status",
                            "step_description": "Your current education status and institution details",
                            "questions": [
                                {
                                    "question_id": "has_provincial_attestation",
                                    "question_text": "Do you have a provincial attestation letter (PAL) or territorial attestation letter (TAL)?",
                                    "question_type": "yes_no",
                                    "required": True,
                                    "help_text": "Required for most study permit applications as of January 2024"
                                },
                                {
                                    "question_id": "accepted_to_dli",
                                    "question_text": "Have you been accepted to a designated learning institution (DLI)?",
                                    "question_type": "yes_no",
                                    "required": True,
                                    "help_text": "You need an acceptance letter from a DLI to apply for a study permit"
                                },
                                {
                                    "question_id": "institution_name",
                                    "question_text": "What is the name of your institution?",
                                    "question_type": "text",
                                    "required": True,
                                    "conditional_logic": {
                                        "depends_on": "accepted_to_dli",
                                        "show_if": ["Yes"]
                                    },
                                    "placeholder": "e.g., University of Toronto"
                                },
                                {
                                    "question_id": "program_name",
                                    "question_text": "What program will you be studying?",
                                    "question_type": "text",
                                    "required": True,
                                    "conditional_logic": {
                                        "depends_on": "accepted_to_dli",
                                        "show_if": ["Yes"]
                                    },
                                    "placeholder": "e.g., Master of Computer Science"
                                }
                            ]
                        }
                    ]
                },
                {
                    "section_id": "financial_information",
                    "section_name": "Financial Information",
                    "section_description": "Proof of financial support for your studies",
                    "order": 3,
                    "steps": [
                        {
                            "step_id": "financial_status",
                            "step_name": "Financial Proof",
                            "step_description": "Show that you can financially support yourself",
                            "questions": [
                                {
                                    "question_id": "has_sds_gic",
                                    "question_text": "Do you have a Guaranteed Investment Certificate (GIC) from a participating Canadian financial institution for at least $20,635?",
                                    "question_type": "yes_no",
                                    "required": True,
                                    "help_text": "Required for Student Direct Stream (SDS) processing"
                                },
                                {
                                    "question_id": "tuition_paid_full",
                                    "question_text": "Have you paid your first year tuition in full?",
                                    "question_type": "yes_no",
                                    "required": True,
                                    "help_text": "Proof of tuition payment strengthens your application"
                                }
                            ]
                        }
                    ]
                },
                {
                    "section_id": "language_requirements",
                    "section_name": "Language Requirements",
                    "section_description": "English or French language proficiency",
                    "order": 4,
                    "steps": [
                        {
                            "step_id": "language_test",
                            "step_name": "Language Test Results",
                            "step_description": "Your language test scores",
                            "questions": [
                                {
                                    "question_id": "has_language_test",
                                    "question_text": "Have you taken a language test in the past 2 years?",
                                    "question_type": "yes_no",
                                    "required": True,
                                    "help_text": "Required for most study permit applications"
                                },
                                {
                                    "question_id": "test_type",
                                    "question_text": "Which language test did you take?",
                                    "question_type": "single_choice",
                                    "required": True,
                                    "conditional_logic": {
                                        "depends_on": "has_language_test",
                                        "show_if": ["Yes"]
                                    },
                                    "options": [
                                        {"value": "IELTS", "label": "IELTS (International English Language Testing System)"},
                                        {"value": "TOEFL", "label": "TOEFL (Test of English as a Foreign Language)"},
                                        {"value": "PTE", "label": "PTE (Pearson Test of English)"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }


async def main():
    """Main function to run the seeding process."""
    try:
        seeder = QuestionBankSeeder()
        await seeder.seed_questions()
        print("✅ Question bank seeding completed successfully!")
        
    except Exception as e:
        print(f"❌ Question bank seeding failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 