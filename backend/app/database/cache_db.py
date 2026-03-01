"""
Redis Cache Database Integration for Agent Arena
Provides caching layer for agent memory, conversation history, and temporary data.
"""
import redis
import json
from typing import Optional, Any, Dict, List
from datetime import timedelta

class RedisCache:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None):
        """
        Initialize Redis connection
        
        Args:
            host: Redis server host
            port: Redis server port  
            db: Redis database number
            password: Redis password (if required)
        """
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
    def set_value(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a value in Redis cache
        
        Args:
            key: Cache key
            value: Value to store (will be JSON serialized if not string)
            expire: Expiration time in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            if isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = json.dumps(value, default=str)
            
            if expire:
                self.redis_client.setex(key, expire, serialized_value)
            else:
                self.redis_client.set(key, serialized_value)
            return True
        except Exception as e:
            print(f"Error setting cache value: {e}")
            return False
    
    def get_value(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis cache
        
        Args:
            key: Cache key
            
        Returns:
            Value if exists, None otherwise
        """
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to parse as JSON, if it fails return as string
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            print(f"Error getting cache value: {e}")
            return None
    
    def delete_key(self, key: str) -> bool:
        """Delete a key from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            print(f"Error deleting cache key: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"Error checking cache key existence: {e}")
            return False
    
    def set_hash(self, name: str, mapping: Dict[str, Any]) -> bool:
        """
        Set hash fields in Redis
        
        Args:
            name: Hash name
            mapping: Dictionary of field-value pairs
            
        Returns:
            bool: True if successful
        """
        try:
            # Convert values to strings
            string_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, str):
                    string_mapping[key] = value
                else:
                    string_mapping[key] = json.dumps(value, default=str)
            
            self.redis_client.hset(name, mapping=string_mapping)
            return True
        except Exception as e:
            print(f"Error setting hash: {e}")
            return False
    
    def get_hash(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get all fields from a hash
        
        Args:
            name: Hash name
            
        Returns:
            Dictionary of field-value pairs or None if hash doesn't exist
        """
        try:
            hash_data = self.redis_client.hgetall(name)
            if not hash_data:
                return None
            
            # Parse JSON values
            parsed_data = {}
            for key, value in hash_data.items():
                try:
                    parsed_data[key] = json.loads(value)
                except json.JSONDecodeError:
                    parsed_data[key] = value
            return parsed_data
        except Exception as e:
            print(f"Error getting hash: {e}")
            return None
    
    def delete_hash_field(self, name: str, key: str) -> bool:
        """Delete a field from hash"""
        try:
            return bool(self.redis_client.hdel(name, key))
        except Exception as e:
            print(f"Error deleting hash field: {e}")
            return False
    
    def add_to_set(self, name: str, value: Any) -> bool:
        """Add value to Redis set"""
        try:
            if isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = json.dumps(value, default=str)
            self.redis_client.sadd(name, serialized_value)
            return True
        except Exception as e:
            print(f"Error adding to set: {e}")
            return False
    
    def get_set_members(self, name: str) -> List[Any]:
        """Get all members from Redis set"""
        try:
            members = self.redis_client.smembers(name)
            parsed_members = []
            for member in members:
                try:
                    parsed_members.append(json.loads(member))
                except json.JSONDecodeError:
                    parsed_members.append(member)
            return parsed_members
        except Exception as e:
            print(f"Error getting set members: {e}")
            return []
    
    def remove_from_set(self, name: str, value: Any) -> bool:
        """Remove value from Redis set"""
        try:
            if isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = json.dumps(value, default=str)
            return bool(self.redis_client.srem(name, serialized_value))
        except Exception as e:
            print(f"Error removing from set: {e}")
            return False
    
    def publish_message(self, channel: str, message: Any) -> bool:
        """
        Publish message to Redis channel
        
        Args:
            channel: Channel name
            message: Message to publish
            
        Returns:
            bool: True if successful
        """
        try:
            if isinstance(message, str):
                serialized_message = message
            else:
                serialized_message = json.dumps(message, default=str)
            self.redis_client.publish(channel, serialized_message)
            return True
        except Exception as e:
            print(f"Error publishing message: {e}")
            return False
    
    def close(self):
        """Close Redis connection"""
        self.redis_client.close()

    async def health_check(self):
        """Health check for Redis."""
        import asyncio
        try:
            await asyncio.to_thread(self.redis_client.ping)
            return "connected"
        except Exception as e:
            return f"error: {e}"

    async def initialize(self):
        """Async init (no-op, connection already in __init__)."""
        pass

# Global Redis instance
redis_cache = None

def init_redis_cache():
    """Initialize global Redis cache instance"""
    global redis_cache
    if redis_cache is None:
        # Get configuration from environment or use defaults
        import os
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        redis_db = int(os.getenv("REDIS_DB", "0"))
        
        redis_cache = RedisCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password
        )
    return redis_cache

def get_redis_cache() -> RedisCache:
    """Get Redis cache instance (initialize if needed)"""
    if redis_cache is None:
        init_redis_cache()
    return redis_cache


def _redis_config_from_env():
    """从环境变量构建 Redis 连接参数；支持 REDIS_URL 或 REDIS_HOST/PORT/PASSWORD/DB。"""
    import os
    url = os.getenv("REDIS_URL", "").strip()
    if url:
        # redis://[:password@]host:port/db
        from urllib.parse import urlparse
        p = urlparse(url)
        host = p.hostname or "localhost"
        port = p.port or 6379
        password = p.password or None
        db = 0
        if p.path and len(p.path) > 1:
            try:
                db = int(p.path[1:].split("/")[0])
            except ValueError:
                pass
        return dict(host=host, port=port, db=db, password=password)
    return dict(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD") or None,
    )


# Alias for dependency injection (RedisCache with env-based config)
class CacheDB(RedisCache):
    """CacheDB wrapper: uses REDIS_URL or REDIS_* env, defaults to localhost:6379."""
    def __init__(self):
        super().__init__(**_redis_config_from_env())

# Usage examples:
"""
# Initialize cache
cache = get_redis_cache()

# Store agent memory
agent_memory = {
    "agent_id": "agent_123",
    "conversation_history": [...],
    "preferences": {...}
}
cache.set_value("agent:agent_123:memory", agent_memory, expire=3600)

# Retrieve agent memory
retrieved_memory = cache.get_value("agent:agent_123:memory")

# Store conversation in hash
cache.set_hash("conversation:conv_456", {
    "messages": [...],
    "participants": ["agent_123", "user_789"],
    "created_at": "2026-02-14T22:00:00Z"
})

# Add agent to active agents set
cache.add_to_set("active_agents", "agent_123")

# Publish agent status update
cache.publish_message("agent_status", {
    "agent_id": "agent_123",
    "status": "active",
    "timestamp": "2026-02-14T22:00:00Z"
})
"""