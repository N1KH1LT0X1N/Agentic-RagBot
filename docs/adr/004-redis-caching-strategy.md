# ADR-004: Redis Multi-Level Caching Strategy

## Status
Accepted

## Context
MediGuard AI performs many expensive operations:
- LLM API calls for analysis
- Vector searches in OpenSearch
- Complex biomarker calculations
- Repeated requests for similar data

Without caching, these operations would be repeated unnecessarily, leading to:
- Increased latency for users
- Higher costs from LLM API calls
- Unnecessary load on databases
- Poor user experience

## Decision
Implement a multi-level caching strategy using Redis:
1. **L1 Cache (Memory)**: Fast, temporary cache for frequently accessed data
2. **L2 Cache (Redis)**: Persistent, distributed cache for longer-term storage
3. **Intelligent Promotion**: Automatically promote L2 hits to L1
4. **Smart Invalidation**: Cache invalidation based on data changes
5. **TTL Management**: Different TTLs based on data type

## Consequences

### Positive
- **Performance**: Significant reduction in response times
- **Cost Savings**: Fewer LLM API calls
- **Scalability**: Better resource utilization
- **User Experience**: Faster responses for repeated queries
- **Reliability**: Graceful degradation when caches fail

### Negative
- **Complexity**: Additional caching logic to maintain
- **Memory Usage**: L1 cache consumes application memory
- **Stale Data**: Risk of serving stale data if not invalidated properly
- **Infrastructure**: Requires Redis deployment and maintenance

## Implementation
```python
class CacheManager:
    def __init__(self, l1_backend: CacheBackend, l2_backend: Optional[CacheBackend] = None):
        self.l1 = l1_backend  # Fast memory cache
        self.l2 = l2_backend  # Redis cache
        
    async def get(self, key: str) -> Optional[Any]:
        # Try L1 first
        value = await self.l1.get(key)
        if value is not None:
            return value
            
        # Try L2 and promote to L1
        if self.l2:
            value = await self.l2.get(key)
            if value is not None:
                await self.l1.set(key, value, ttl=l1_ttl)
                return value
```

Cache decorators for automatic caching:
```python
@cached(ttl=300, key_prefix="analysis:")
async def analyze_biomarkers(biomarkers: Dict[str, float]):
    # Expensive analysis logic
    pass
```

## Notes
- L1 cache has a maximum size with LRU eviction
- L2 cache persists across application restarts
- Cache keys include version numbers for easy invalidation
- Monitoring tracks hit rates and performance metrics
- Cache warming strategies for frequently accessed data
