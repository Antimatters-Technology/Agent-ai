from datetime import datetime
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class ConsentTracker:
    def __init__(self):
        self.consent_types = [
            "data_processing",
            "document_storage", 
            "ai_analysis",
            "third_party_sharing",
            "marketing_communications"
        ]
    
    def record_consent(self, user_id: str, consent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record user consent"""
        try:
            consent_record = {
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "ip_address": consent_data.get("ip_address"),
                "user_agent": consent_data.get("user_agent"),
                "consents": consent_data.get("consents", {}),
                "version": "1.0",  # Privacy policy version
                "method": consent_data.get("method", "web_form")
            }
            
            # Validate all required consents
            missing_consents = []
            for consent_type in self.consent_types:
                if consent_type not in consent_record["consents"]:
                    missing_consents.append(consent_type)
            
            if missing_consents:
                raise ValueError(f"Missing required consents: {missing_consents}")
            
            # Store in database (mock implementation)
            consent_id = self._store_consent(consent_record)
            
            logger.info(f"Recorded consent {consent_id} for user {user_id}")
            
            return {
                "consent_id": consent_id,
                "status": "recorded",
                "timestamp": consent_record["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Consent recording failed: {str(e)}")
            raise
    
    def check_consent(self, user_id: str, consent_type: str) -> bool:
        """Check if user has given specific consent"""
        try:
            # Mock implementation - replace with actual DB query
            consent_records = self._get_user_consents(user_id)
            
            if not consent_records:
                return False
            
            latest_consent = max(consent_records, key=lambda x: x["timestamp"])
            return latest_consent.get("consents", {}).get(consent_type, False)
            
        except Exception as e:
            logger.error(f"Consent check failed: {str(e)}")
            return False
    
    def withdraw_consent(self, user_id: str, consent_type: str) -> Dict[str, Any]:
        """Record consent withdrawal"""
        try:
            withdrawal_record = {
                "user_id": user_id,
                "consent_type": consent_type,
                "timestamp": datetime.now().isoformat(),
                "action": "withdraw"
            }
            
            # Store withdrawal (mock implementation)
            withdrawal_id = self._store_withdrawal(withdrawal_record)
            
            logger.info(f"Recorded consent withdrawal {withdrawal_id} for user {user_id}")
            
            return {
                "withdrawal_id": withdrawal_id,
                "status": "withdrawn",
                "timestamp": withdrawal_record["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Consent withdrawal failed: {str(e)}")
            raise
    
    def _store_consent(self, consent_record: Dict) -> str:
        """Store consent record in database"""
        # Mock implementation - replace with actual DB storage
        import uuid
        return str(uuid.uuid4())
    
    def _store_withdrawal(self, withdrawal_record: Dict) -> str:
        """Store withdrawal record in database"""
        # Mock implementation - replace with actual DB storage
        import uuid
        return str(uuid.uuid4())
    
    def _get_user_consents(self, user_id: str) -> List[Dict]:
        """Get all consent records for user"""
        # Mock implementation - replace with actual DB query
        return []