import asyncio
import json
from typing import Dict, Any
import pytesseract
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class DocumentParser:
    def __init__(self):
        self.supported_formats = ['.pdf', '.jpg', '.jpeg', '.png']
    
    async def parse_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Extract text from document using OCR"""
        try:
            # Convert to image if needed
            image = Image.open(io.BytesIO(file_content))
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            # Basic document type detection
            doc_type = self._detect_document_type(text, filename)
            
            return {
                "filename": filename,
                "extracted_text": text,
                "document_type": doc_type,
                "status": "completed",
                "confidence": 0.85  # Mock confidence
            }
        except Exception as e:
            logger.error(f"OCR failed for {filename}: {str(e)}")
            return {
                "filename": filename,
                "extracted_text": "",
                "document_type": "unknown",
                "status": "failed",
                "error": str(e)
            }
    
    def _detect_document_type(self, text: str, filename: str) -> str:
        """Simple document type detection"""
        text_lower = text.lower()
        
        if "passport" in text_lower or "republic of india" in text_lower:
            return "passport"
        elif "mark" in text_lower and ("grade" in text_lower or "transcript" in text_lower):
            return "academic_transcript"
        elif "bank" in text_lower and "statement" in text_lower:
            return "bank_statement"
        elif "ielts" in text_lower or "toefl" in text_lower:
            return "language_test"
        else:
            return "other"