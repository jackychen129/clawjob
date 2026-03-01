"""
Vector database integration for Agent Arena using ChromaDB.
Provides semantic search and vector storage capabilities for agentic applications.
"""
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class VectorDatabase:
    def __init__(self, persist_directory: str = None):
        """Initialize ChromaDB vector database."""
        persist_directory = persist_directory or os.getenv("CHROMA_DB_PATH", "./data/chroma")
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collections = {}
        
    def create_collection(self, name: str, embedding_function=None):
        """Create a new collection in the vector database."""
        try:
            if embedding_function:
                collection = self.client.create_collection(
                    name=name,
                    embedding_function=embedding_function
                )
            else:
                collection = self.client.create_collection(name=name)
            self.collections[name] = collection
            logger.info(f"Created collection: {name}")
            return collection
        except Exception as e:
            logger.error(f"Failed to create collection {name}: {e}")
            raise
            
    def get_or_create_collection(self, name: str, embedding_function=None):
        """Get existing collection or create new one."""
        try:
            if name in self.collections:
                return self.collections[name]
                
            # Try to get existing collection
            try:
                collection = self.client.get_collection(name)
                self.collections[name] = collection
                return collection
            except:
                # Collection doesn't exist, create it
                return self.create_collection(name, embedding_function)
                
        except Exception as e:
            logger.error(f"Failed to get or create collection {name}: {e}")
            raise
            
    def add_documents(self, collection_name: str, documents: List[str], 
                     metadatas: List[Dict] = None, ids: List[str] = None):
        """Add documents to a collection."""
        try:
            collection = self.get_or_create_collection(collection_name)
            
            if ids is None:
                # Generate IDs if not provided
                start_id = collection.count() + 1
                ids = [f"doc_{start_id + i}" for i in range(len(documents))]
                
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to add documents to {collection_name}: {e}")
            raise
            
    def query(self, collection_name: str, query_text: str, 
              n_results: int = 5, where: Dict = None) -> Dict[str, Any]:
        """Query the vector database for similar documents."""
        try:
            collection = self.get_or_create_collection(collection_name)
            
            if where:
                results = collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                    where=where
                )
            else:
                results = collection.query(
                    query_texts=[query_text],
                    n_results=n_results
                )
                
            return results
            
        except Exception as e:
            logger.error(f"Failed to query {collection_name}: {e}")
            raise
            
    def delete_collection(self, collection_name: str):
        """Delete a collection from the database."""
        try:
            self.client.delete_collection(collection_name)
            if collection_name in self.collections:
                del self.collections[collection_name]
            logger.info(f"Deleted collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise
            
    def list_collections(self) -> List[str]:
        """List all collections in the database."""
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
            
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    async def health_check(self):
        """Health check for the vector database."""
        try:
            self.client.list_collections()
            return "connected"
        except Exception as e:
            logger.error(f"Vector DB health check failed: {e}")
            return f"error: {e}"

    async def initialize(self):
        """Async init (no-op for ChromaDB)."""
        pass


# Alias for main/task_system
VectorDB = VectorDatabase

# Global vector database instance
vector_db = VectorDatabase()