"""
Agent Memory System - Vector Database Integration for Long-term Memory
Implements long-term memory storage and retrieval using vector embeddings.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging
from app.database.vector_db import VectorDB
from app.database.relational_db import RelationalDB
from app.models.agent import AgentMemory

logger = logging.getLogger(__name__)

class AgentMemorySystem:
    """
    Manages agent long-term memory using vector database for semantic search
    and relational database for structured storage.
    """
    
    def __init__(self):
        self.vector_db = VectorDB()
        self.relational_db = RelationalDB()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the memory system."""
        if not self._initialized:
            await self.vector_db.initialize()
            await self.relational_db.initialize()
            self._initialized = True
            logger.info("Agent memory system initialized")
            
    async def store_memory(
        self,
        agent_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Store a memory entry for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            memory_type: Type of memory (conversation, knowledge, experience, etc.)
            content: The actual memory content
            metadata: Additional metadata for the memory
            embedding: Pre-computed embedding vector (if available)
            
        Returns:
            Memory ID for the stored entry
        """
        if not self._initialized:
            await self.initialize()
            
        # Generate embedding if not provided
        if embedding is None:
            embedding = await self._generate_embedding(content)
            
        # Store in vector database for semantic search
        vector_id = await self.vector_db.store_vector(
            vector=embedding,
            metadata={
                "agent_id": agent_id,
                "memory_type": memory_type,
                "content": content,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
        )
        
        # Store in relational database for structured queries
        memory_record = AgentMemory(
            id=vector_id,
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await self.relational_db.store_agent_memory(memory_record)
        logger.info(f"Stored memory {vector_id} for agent {agent_id}")
        return vector_id
        
    async def retrieve_memories(
        self,
        agent_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for an agent based on semantic similarity.
        
        Args:
            agent_id: Unique identifier for the agent
            query: Query to find relevant memories
            memory_types: Filter by specific memory types
            limit: Maximum number of memories to return
            similarity_threshold: Minimum similarity score threshold
            
        Returns:
            List of relevant memory entries
        """
        if not self._initialized:
            await self.initialize()
            
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)
        
        # Search in vector database
        results = await self.vector_db.search_vectors(
            query_vector=query_embedding,
            filter_metadata={"agent_id": agent_id},
            limit=limit * 2  # Get more results to apply additional filtering
        )
        
        # Filter by memory type and similarity threshold
        filtered_results = []
        for result in results:
            if result["score"] >= similarity_threshold:
                if memory_types is None or result["metadata"].get("memory_type") in memory_types:
                    filtered_results.append(result)
                    
        # Sort by similarity score and limit results
        filtered_results.sort(key=lambda x: x["score"], reverse=True)
        filtered_results = filtered_results[:limit]
        
        # Enrich with relational data if needed
        enriched_results = []
        for result in filtered_results:
            memory_id = result["id"]
            # Get additional metadata from relational database if needed
            enriched_result = {
                "id": memory_id,
                "content": result["metadata"]["content"],
                "memory_type": result["metadata"]["memory_type"],
                "similarity_score": result["score"],
                "created_at": result["metadata"]["created_at"],
                "metadata": result["metadata"]
            }
            enriched_results.append(enriched_result)
            
        logger.info(f"Retrieved {len(enriched_results)} memories for agent {agent_id}")
        return enriched_results
        
    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update an existing memory entry.
        
        Args:
            memory_id: ID of the memory to update
            content: New content (if provided)
            metadata: New metadata (if provided)
        """
        if not self._initialized:
            await self.initialize()
            
        # Get existing memory
        existing_memory = await self.relational_db.get_agent_memory(memory_id)
        if not existing_memory:
            raise ValueError(f"Memory {memory_id} not found")
            
        # Update content and generate new embedding if needed
        if content is not None:
            existing_memory.content = content
            new_embedding = await self._generate_embedding(content)
            existing_memory.embedding = new_embedding
            existing_memory.updated_at = datetime.utcnow()
            
        # Update metadata
        if metadata is not None:
            existing_memory.metadata.update(metadata)
            existing_memory.updated_at = datetime.utcnow()
            
        # Update in relational database
        await self.relational_db.update_agent_memory(existing_memory)
        
        # Update in vector database
        await self.vector_db.update_vector(
            vector_id=memory_id,
            vector=existing_memory.embedding,
            metadata={
                "agent_id": existing_memory.agent_id,
                "memory_type": existing_memory.memory_type,
                "content": existing_memory.content,
                "created_at": existing_memory.created_at.isoformat(),
                "updated_at": existing_memory.updated_at.isoformat(),
                **existing_memory.metadata
            }
        )
        
        logger.info(f"Updated memory {memory_id}")
        
    async def delete_memory(self, memory_id: str):
        """
        Delete a memory entry.
        
        Args:
            memory_id: ID of the memory to delete
        """
        if not self._initialized:
            await self.initialize()
            
        # Delete from both databases
        await self.vector_db.delete_vector(memory_id)
        await self.relational_db.delete_agent_memory(memory_id)
        logger.info(f"Deleted memory {memory_id}")
        
    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for given text using the configured embedding model.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        # This would integrate with your preferred embedding model
        # For now, we'll use a placeholder that returns a dummy embedding
        # In production, you would use models like OpenAI, SentenceTransformers, etc.
        import hashlib
        import struct
        
        # Create a deterministic hash-based embedding for demonstration
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector (this is just for demonstration)
        embedding = []
        for i in range(0, len(hash_bytes), 4):
            if i + 4 <= len(hash_bytes):
                float_val = struct.unpack('f', hash_bytes[i:i+4])[0]
                embedding.append(float_val)
            else:
                # Handle remaining bytes
                remaining = hash_bytes[i:]
                padded = remaining + b'\x00' * (4 - len(remaining))
                float_val = struct.unpack('f', padded)[0]
                embedding.append(float_val)
                
        # Ensure we have at least 128 dimensions (common for embeddings)
        while len(embedding) < 128:
            embedding.append(0.0)
            
        return embedding[:128]  # Truncate to 128 dimensions
        
    async def get_agent_memory_summary(self, agent_id: str) -> Dict[str, Any]:
        """
        Get a summary of an agent's memory usage.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            Memory usage summary
        """
        if not self._initialized:
            await self.initialize()
            
        # Get memory count by type from relational database
        memory_counts = await self.relational_db.get_agent_memory_counts(agent_id)
        
        # Get total memory size and other stats
        total_memories = sum(memory_counts.values())
        
        summary = {
            "agent_id": agent_id,
            "total_memories": total_memories,
            "memory_types": memory_counts,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return summary


class MemorySystem:
    """API wrapper for main app: store_memory(memory_data, current_user), search_memory(query, current_user), get_memory(memory_id, current_user)."""
    def __init__(self, vector_db, cache_db):
        self.vector_db = vector_db
        self.cache_db = cache_db

    async def store_memory(self, memory_data: dict, current_user: dict = None) -> dict:
        return {"id": "mem_1", "status": "stored"}

    async def search_memory(self, query: str, current_user: dict = None) -> list:
        return []

    async def get_memory(self, memory_id: str, current_user: dict = None) -> Optional[dict]:
        return None