import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import uuid
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_document(self, text: str, metadata: Dict[str, Any]) -> str:
        """Add document to vector store"""
        try:
            doc_id = str(uuid.uuid4())
            
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.info(f"Added document {doc_id} to vector store")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add document: {str(e)}")
            raise
    
    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def update_document(self, doc_id: str, text: str, metadata: Dict[str, Any]):
        """Update existing document"""
        try:
            self.collection.update(
                ids=[doc_id],
                documents=[text],
                metadatas=[metadata]
            )
            logger.info(f"Updated document {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {str(e)}")
            raise
    
    def delete_document(self, doc_id: str):
        """Delete document from vector store"""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            raise