# Troubleshooting Guide

This guide helps diagnose and resolve common issues with MediGuard AI.

## Table of Contents
1. [Startup Issues](#startup-issues)
2. [Service Connectivity](#service-connectivity)
3. [Performance Issues](#performance-issues)
4. [API Errors](#api-errors)
5. [Database Issues](#database-issues)
6. [Memory and CPU Issues](#memory-and-cpu-issues)
7. [Logging and Monitoring](#logging-and-monitoring)
8. [Common Error Messages](#common-error-messages)

## Startup Issues

### Application Won't Start

**Symptoms:**
- Application exits immediately
- Port already in use errors
- Module import errors

**Solutions:**

1. **Check port availability:**
   ```bash
   # Check if port 8000 is in use
   netstat -tulpn | grep 8000
   # Or on Windows
   netstat -ano | findstr 8000
   ```

2. **Verify Python environment:**
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   # On Windows
   venv\Scripts\activate
   
   # Check dependencies
   pip list
   ```

3. **Check environment variables:**
   ```bash
   # Verify required variables are set
   env | grep -E "(GROQ|REDIS|OPENSEARCH)"
   ```

4. **Common startup errors and fixes:**

   | Error | Cause | Solution |
   |-------|-------|----------|
   | `ModuleNotFoundError` | Missing dependencies | `pip install -r requirements.txt` |
   | `Permission denied` | Port requires privileges | Use port > 1024 or run with sudo |
   | `Address already in use` | Another process using port | Kill process or use different port |

### Docker Container Issues

**Symptoms:**
- Container fails to start
- Health check failures
- Volume mount errors

**Solutions:**

1. **Check container logs:**
   ```bash
   docker logs mediguard-api
   docker-compose logs api
   ```

2. **Verify Docker resources:**
   ```bash
   # Check Docker resource usage
   docker stats
   
   # Check disk space
   docker system df
   ```

3. **Rebuild container:**
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

## Service Connectivity

### OpenSearch Connection Issues

**Symptoms:**
- Search requests failing
- Connection timeout errors
- Authentication failures

**Diagnosis:**
```bash
# Check OpenSearch health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Test from application
curl http://localhost:8000/health/service/opensearch
```

**Solutions:**

1. **Verify OpenSearch is running:**
   ```bash
   docker-compose ps opensearch
   docker-compose restart opensearch
   ```

2. **Check network connectivity:**
   ```bash
   # Test connection
   telnet localhost 9200
   
   # Check firewall
   sudo ufw status
   ```

3. **Fix authentication:**
   ```yaml
   # In docker-compose.yml
   environment:
     - DISABLE_SECURITY_PLUGIN=true  # For development
   ```

### Redis Connection Issues

**Symptoms:**
- Cache misses
- Session data loss
- Rate limiting not working

**Diagnosis:**
```bash
# Test Redis connection
redis-cli ping

# Check from application
curl http://localhost:8000/health/service/redis
```

**Solutions:**

1. **Restart Redis:**
   ```bash
   docker-compose restart redis
   ```

2. **Clear corrupted data:**
   ```bash
   redis-cli FLUSHALL
   ```

3. **Check memory limits:**
   ```bash
   # In redis-cli
   INFO memory
   ```

### Ollama/LLM Connection Issues

**Symptoms:**
- LLM requests timing out
- Model not found errors
- Slow responses

**Diagnosis:**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Test model
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.3",
  "prompt": "Test"
}'
```

**Solutions:**

1. **Pull required models:**
   ```bash
   docker-compose exec ollama ollama pull llama3.3
   ```

2. **Check GPU availability:**
   ```bash
   nvidia-smi
   ```

3. **Adjust timeouts:**
   ```python
   # In settings
   OLLAMA_TIMEOUT = 120  # Increase timeout
   ```

## Performance Issues

### Slow API Responses

**Symptoms:**
- Requests taking > 5 seconds
- Timeouts in client applications
- High CPU usage

**Diagnosis:**

1. **Check response times:**
   ```bash
   # Use curl with timing
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
   
   # Monitor with metrics
   curl http://localhost:8000/metrics | grep http_request_duration
   ```

2. **Profile the application:**
   ```bash
   # Use py-spy
   pip install py-spy
   py-spy top --pid <pid>
   ```

**Solutions:**

1. **Enable caching:**
   ```python
   # Add caching to expensive operations
   from src.services.cache.advanced_cache import cached
   
   @cached(ttl=300)
   async def expensive_operation():
       ...
   ```

2. **Optimize database queries:**
   ```python
   # Use optimized queries
   from src.services.opensearch.client import make_opensearch_client
   client = make_opensearch_client()
   results = client.search_bm25_optimized(query, min_score=0.5)
   ```

3. **Scale horizontally:**
   ```bash
   # Run multiple instances
   docker-compose up -d --scale api=3
   ```

### Memory Leaks

**Symptoms:**
- Memory usage increasing over time
- Out of memory errors
- Container restarts

**Diagnosis:**

1. **Monitor memory usage:**
   ```bash
   # Check container memory
   docker stats
   
   # Check process memory
   ps aux | grep python
   ```

2. **Find memory leaks:**
   ```bash
   # Use memory-profiler
   pip install memory-profiler
   python -m memory_profiler script.py
   ```

**Solutions:**

1. **Fix circular references:**
   ```python
   # Use weak references
   import weakref
   
   class Parent:
       def __init__(self):
           self.children = weakref.WeakSet()
   ```

2. **Clear caches:**
   ```python
   # Periodically clear caches
   from src.services.cache.advanced_cache import CacheInvalidator
   await CacheInvalidator.invalidate_by_pattern("*")
   ```

3. **Increase memory limits:**
   ```yaml
   # In docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 4G
   ```

## API Errors

### 422 Validation Errors

**Symptoms:**
- `{"detail": [...]}` with validation errors
- Requests rejected with status 422

**Common causes:**

1. **Missing required fields:**
   ```json
   // Wrong
   {"biomarkers": {}}
   
   // Right
   {"biomarkers": {"Glucose": 100}}
   ```

2. **Invalid data types:**
   ```json
   // Wrong
   {"biomarkers": {"Glucose": "high"}}
   
   // Right
   {"biomarkers": {"Glucose": 150}}
   ```

3. **Out of range values:**
   ```json
   // Check API docs for valid ranges
   curl http://localhost:8000/docs
   ```

### 500 Internal Server Errors

**Symptoms:**
- Generic error messages
- Stack traces in logs

**Diagnosis:**

1. **Check application logs:**
   ```bash
   docker-compose logs -f api | grep ERROR
   ```

2. **Enable debug mode:**
   ```bash
   export DEBUG=true
   uvicorn src.main:app --reload
   ```

**Common causes:**

| Error | Solution |
|-------|----------|
| Database connection lost | Restart database services |
| External service down | Check service health endpoints |
| Memory error | Increase memory or optimize code |
| Configuration error | Verify environment variables |

### 503 Service Unavailable

**Symptoms:**
- Service temporarily unavailable
- Health check failures

**Solutions:**

1. **Check service dependencies:**
   ```bash
   curl http://localhost:8000/health/detailed
   ```

2. **Restart affected services:**
   ```bash
   docker-compose restart
   ```

3. **Check rate limits:**
   ```bash
   # Check rate limit headers
   curl -I http://localhost:8000/analyze/structured
   ```

## Database Issues

### OpenSearch Index Problems

**Symptoms:**
- Search returning no results
- Index not found errors
- Mapping errors

**Diagnosis:**

1. **Check index status:**
   ```bash
   curl -X GET "localhost:9200/_cat/indices?v"
   ```

2. **Verify mapping:**
   ```bash
   curl -X GET "localhost:9200/medical_chunks/_mapping?pretty"
   ```

**Solutions:**

1. **Recreate index:**
   ```bash
   # Delete and recreate
   curl -X DELETE "localhost:9200/medical_chunks"
   # Restart application to recreate
   ```

2. **Fix mapping:**
   ```python
   # Update index config
   from src.services.opensearch.index_config import MEDICAL_CHUNKS_MAPPING
   client.ensure_index(MEDICAL_CHUNKS_MAPPING)
   ```

### Data Corruption

**Symptoms:**
- Inconsistent search results
- Missing documents
- Strange query behavior

**Solutions:**

1. **Verify data integrity:**
   ```bash
   # Count documents
   curl -X GET "localhost:9200/medical_chunks/_count"
   ```

2. **Reindex data:**
   ```python
   # Use indexing service
   from src.services.indexing.service import IndexingService
   service = IndexingService()
   await service.reindex_all()
   ```

## Logging and Monitoring

### Enable Debug Logging

1. **Set log level:**
   ```bash
   export LOG_LEVEL=DEBUG
   export LOG_TO_FILE=true
   ```

2. **View logs:**
   ```bash
   # Real-time logs
   tail -f data/logs/mediguard.log
   
   # Filter by level
   grep "ERROR" data/logs/mediguard.log
   ```

### Monitor Metrics

1. **Check Prometheus metrics:**
   ```bash
   curl http://localhost:8000/metrics | grep http_
   ```

2. **View Grafana dashboard:**
   - Navigate to http://localhost:3000
   - Import `monitoring/grafana-dashboard.json`

### Performance Profiling

1. **Enable profiling:**
   ```python
   # Add to main.py
   from pyinstrument import Profiler
   
   @app.middleware("http")
   async def profile_requests(request: Request, call_next):
       profiler = Profiler()
       profiler.start()
       response = await call_next(request)
       profiler.stop()
       print(profiler.output_text(unicode=True, color=True))
       return response
   ```

## Common Error Messages

### "Service unavailable" in logs

**Meaning:** A required service (OpenSearch, Redis, etc.) is not responding.

**Fix:**
1. Check service status: `docker-compose ps`
2. Restart service: `docker-compose restart <service>`
3. Check logs: `docker-compose logs <service>`

### "Rate limit exceeded"

**Meaning:** Too many requests from a client.

**Fix:**
1. Wait and retry
2. Check `Retry-After` header
3. Implement client-side rate limiting

### "Invalid token" or "Authentication failed"

**Meaning:** Invalid API key or token.

**Fix:**
1. Verify API key is correct
2. Check token hasn't expired
3. Ensure proper header format: `Authorization: Bearer <token>`

### "Query too large" or "Request entity too large"

**Meaning:** Request exceeds size limits.

**Fix:**
1. Reduce request size
2. Use pagination
3. Increase limits in configuration

### "Connection pool exhausted"

**Meaning:** Too many concurrent database connections.

**Fix:**
1. Increase pool size
2. Add connection timeout
3. Implement request queuing

## Emergency Procedures

### Full System Recovery

```bash
# 1. Stop all services
docker-compose down

# 2. Clear corrupted data (WARNING: This deletes data!)
docker volume rm agentic-ragbot_opensearch_data
docker volume rm agentic-ragbot_redis_data

# 3. Restart with fresh data
docker-compose up -d

# 4. Wait for services to be ready
sleep 30

# 5. Verify health
curl http://localhost:8000/health/detailed
```

### Backup and Restore

```bash
# Backup OpenSearch
curl -X POST "localhost:9200/_snapshot/backup/snapshot_1"

# Backup Redis
docker-compose exec redis redis-cli BGSAVE

# Restore from backup
# See DEPLOYMENT.md for detailed instructions
```

### Performance Emergency

```bash
# 1. Scale up services
docker-compose up -d --scale api=5

# 2. Clear all caches
curl -X DELETE http://localhost:8000/admin/cache/clear

# 3. Enable emergency mode
export EMERGENCY_MODE=true
# This disables non-essential features
```

## Getting Help

1. **Check logs first:** Always check application logs for error details
2. **Search issues:** Look for similar issues in GitHub
3. **Collect information:**
   - Error messages
   - Logs
   - System specs
   - Steps to reproduce
4. **Create issue:** Include all relevant information in GitHub issue

### Contact Information

- **Documentation:** Check `/docs` directory
- **Issues:** GitHub Issues
- **Emergency:** Check DEPLOYMENT.md for emergency contacts
