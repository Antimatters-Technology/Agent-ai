import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or generate new one"""
        key_b64 = os.getenv("ENCRYPTION_KEY")
        
        if key_b64:
            return base64.urlsafe_b64decode(key_b64)
        else:
            # Generate new key (for development only)
            key = Fernet.generate_key()
            logger.warning("Generated new encryption key - store ENCRYPTION_KEY in production")
            return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def encrypt_file(self, file_content: bytes) -> bytes:
        """Encrypt file content"""
        try:
            return self.cipher.encrypt(file_content)
        except Exception as e:
            logger.error(f"File encryption failed: {str(e)}")
            raise
    
    def decrypt_file(self, encrypted_content: bytes) -> bytes:
        """Decrypt file content"""
        try:
            return self.cipher.decrypt(encrypted_content)
        except Exception as e:
            logger.error(f"File decryption failed: {str(e)}")
            raise