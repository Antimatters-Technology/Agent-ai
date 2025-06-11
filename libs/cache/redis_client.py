import redis.asyncio as redis
import json
from typing import Any, Optional
import os

class RedisClient:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client = None
    
    async def connect(self):
        self.client = redis.from_url(self.redis_url)
    
    async def set(self, key: str, value: Any, expire: int = 3600):
        """Set value with expiration"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(key, value, ex=expire)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value and try to parse as JSON"""
        value = await self.client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.decode()
        return None
    
    async def delete(self, key: str):
        """Delete key"""
        await self.client.delete(key)
    
    async def close(self):
        if self.client:
            await self.client.close()