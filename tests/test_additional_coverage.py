"""
Additional tests to increase coverage to 70%+.
Tests for services, utilities, and edge cases.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json

# Test services
class TestEmbeddingService:
    """Test embedding service functionality."""
    
    @pytest.mark.asyncio
    async def test_embedding_service_initialization(self):
        """Test embedding service can be initialized."""
        from src.services.embeddings.service import make_embedding_service
        
        with patch('src.services.embeddings.service.get_settings') as mock_settings:
            mock_settings.return_value.EMBEDDING_PROVIDER = "openai"
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            
            service = make_embedding_service()
            assert service is not None
            assert hasattr(service, 'embed_query')
    
    @pytest.mark.asyncio
    async def test_embedding_generation(self):
        """Test embedding generation."""
        from src.services.embeddings.service import make_embedding_service
        
        with patch('src.services.embeddings.service.get_settings') as mock_settings:
            mock_settings.return_value.EMBEDDING_PROVIDER = "openai"
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            
            service = make_embedding_service()
            
            with patch.object(service, 'client') as mock_client:
                mock_client.embeddings.create.return_value.data = [
                    Mock(embedding=[0.1, 0.2, 0.3])
                ]
                
                result = service.embed_query("test text")
                assert len(result) == 3
                assert result[0] == 0.1


class TestExtractionService:
    """Test biomarker extraction service."""
    
    @pytest.mark.asyncio
    async def test_extract_biomarkers_from_text(self):
        """Test biomarker extraction from natural language."""
        from src.services.extraction.service import ExtractionService
        
        service = ExtractionService(llm=None)
        
        text = "My glucose is 150 mg/dL and HbA1c is 8.5%"
        result = service._extract_with_regex(text)
        
        assert "glucose" in result
        assert result["glucose"] == 150
        assert "hba1c" in result
        assert result["hba1c"] == 8.5
    
    @pytest.mark.asyncio
    async def test_extract_patient_context(self):
        """Test patient context extraction."""
        from src.services.extraction.service import ExtractionService
        
        service = ExtractionService(llm=None)
        
        text = "I am a 45-year-old male experiencing fatigue"
        result = service._extract_context(text)
        
        assert result["age"] == 45
        assert result["gender"] == "male"
        assert "fatigue" in result["symptoms"]


class TestCacheService:
    """Test caching service functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test cache set and get operations."""
        from src.services.cache.redis_cache import RedisCache
        
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = None
            mock_client.setex.return_value = True
            
            cache = RedisCache("redis://localhost:6379")
            
            # Test set
            await cache.set("test_key", {"data": "test"}, ttl=60)
            mock_client.setex.assert_called_once()
            
            # Test get miss
            result = await cache.get("test_key")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit scenario."""
        from src.services.cache.redis_cache import RedisCache
        
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            mock_client.get.return_value = json.dumps({"data": "test"}).encode()
            
            cache = RedisCache("redis://localhost:6379")
            result = await cache.get("test_key")
            
            assert result == {"data": "test"}


class TestAdvancedCache:
    """Test advanced caching features."""
    
    @pytest.mark.asyncio
    async def test_cache_manager_l1_l2(self):
        """Test multi-level cache manager."""
        from src.services.cache.advanced_cache import CacheManager, MemoryBackend
        
        l1 = MemoryBackend(max_size=10)
        l2 = MemoryBackend(max_size=100)  # Use memory as mock L2
        manager = CacheManager(l1, l2)
        
        # Test set and get
        await manager.set("test", "value", ttl=60)
        result = await manager.get("test")
        assert result == "value"
        
        # Check stats
        stats = manager.get_stats()
        assert stats['sets'] == 1
        assert stats['l1_hits'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_decorator(self):
        """Test cache decorator functionality."""
        from src.services.cache.advanced_cache import cached, CacheManager, MemoryBackend
        
        # Setup cache
        l1 = MemoryBackend(max_size=10)
        manager = CacheManager(l1)
        
        # Mock get_cache_manager
        with patch('src.services.cache.advanced_cache.get_cache_manager') as mock_get:
            mock_get.return_value = manager
            
            # Apply decorator
            @cached(ttl=60, key_prefix="test:")
            async def expensive_function(x):
                return x * 2
            
            # First call should compute
            result1 = await expensive_function(5)
            assert result1 == 10
            
            # Second call should hit cache
            result2 = await expensive_function(5)
            assert result2 == 10


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_token_bucket_strategy(self):
        """Test token bucket rate limiting."""
        from src.middleware.rate_limiting import TokenBucketStrategy
        
        strategy = TokenBucketStrategy()
        
        # First request should be allowed
        allowed, info = await strategy.is_allowed("test_key", 10, 60)
        assert allowed is True
        assert info['tokens'] == 9  # 10 - 1 used
        
        # Exhaust tokens
        for _ in range(9):
            await strategy.is_allowed("test_key", 10, 60)
        
        # Next request should be denied
        allowed, info = await strategy.is_allowed("test_key", 10, 60)
        assert allowed is False
        assert info['retry_after'] > 0
    
    @pytest.mark.asyncio
    async def test_sliding_window_strategy(self):
        """Test sliding window rate limiting."""
        from src.middleware.rate_limiting import SlidingWindowStrategy
        
        strategy = SlidingWindowStrategy()
        
        # Should allow requests within limit
        for i in range(5):
            allowed, info = await strategy.is_allowed("test_key", 10, 60)
            assert allowed is True
            assert info['remaining'] == 10 - i - 1


class TestErrorHandling:
    """Test enhanced error handling."""
    
    def test_medi_guard_error_creation(self):
        """Test custom error creation."""
        from src.utils.error_handling import MediGuardError, ErrorCategory, ErrorSeverity
        
        error = MediGuardError(
            message="Test error",
            error_code="TEST_001",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details={"field": "test"}
        )
        
        assert error.message == "Test error"
        assert error.error_code == "TEST_001"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.details["field"] == "test"
    
    def test_error_to_dict(self):
        """Test error serialization."""
        from src.utils.error_handling import ValidationError
        
        error = ValidationError(
            message="Invalid input",
            field="email",
            value="invalid-email"
        )
        
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "ValidationError"
        assert error_dict["message"] == "Invalid input"
        assert error_dict["category"] == "validation"
        assert error_dict["details"]["field"] == "email"
    
    def test_structured_logger(self):
        """Test structured logging."""
        from src.utils.error_handling import StructuredLogger
        from unittest.mock import patch
        import tempfile
        
        with tempfile.NamedTemporaryFile() as tmp:
            logger = StructuredLogger("test", Path(tmp.name))
            
            # Test log_error
            from src.utils.error_handling import ValidationError
            error = ValidationError("Test error")
            logger.log_error(error)
            
            # Test log_event
            logger.log_event("test_event", message="Test message")
            
            # Test standard methods
            logger.info("Test info")
            logger.warning("Test warning")


class TestOptimization:
    """Test query optimization."""
    
    def test_query_builder_bm25(self):
        """Test optimized BM25 query building."""
        from src.services.opensearch.query_optimizer import OptimizedQueryBuilder
        
        query = OptimizedQueryBuilder.build_bm25_query(
            query_text="diabetes symptoms",
            top_k=10,
            min_score=0.5
        )
        
        assert query["size"] == 10
        assert query["min_score"] == 0.5
        assert "function_score" in query["query"]
        assert "multi_match" in query["query"]["function_score"]["query"]["bool"]["must"][0]
    
    def test_query_builder_vector(self):
        """Test optimized vector query building."""
        from src.services.opensearch.query_optimizer import OptimizedQueryBuilder
        
        query = OptimizedQueryBuilder.build_vector_query(
            query_vector=[0.1, 0.2, 0.3],
            top_k=5,
            min_score=0.7
        )
        
        assert query["size"] == 5
        assert query["min_score"] == 0.7
        assert "knn" in query["query"]
        assert query["query"]["knn"]["embedding"]["vector"] == [0.1, 0.2, 0.3]
    
    def test_query_cache(self):
        """Test query cache functionality."""
        from src.services.opensearch.query_optimizer import QueryCache
        
        cache = QueryCache(max_size=10, ttl_seconds=60)
        
        # Test cache miss
        result = cache.get("test_query")
        assert result is None
        
        # Test cache set
        test_results = [{"id": 1, "score": 0.9}]
        cache.set("test_query", test_results)
        
        # Test cache hit
        result = cache.get("test_query")
        assert result == test_results
        
        # Test stats
        stats = cache.get_stats()
        assert stats["size"] == 1


class TestHealthChecks:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_opensearch_health_check(self):
        """Test OpenSearch health check."""
        from src.routers.health_extended import check_opensearch_health
        
        with patch('src.services.opensearch.client.make_opensearch_client') as mock_client:
            mock_os = Mock()
            mock_os._client.cluster.health.return_value = {
                "status": "green",
                "number_of_nodes": 1,
                "active_primary_shards": 1,
                "active_shards": 1
            }
            mock_os.doc_count.return_value = 100
            mock_client.return_value = mock_os
            
            health = await check_opensearch_health()
            assert health.status == "healthy"
            assert health.message == "Cluster is healthy"
    
    @pytest.mark.asyncio
    async def test_redis_health_check(self):
        """Test Redis health check."""
        from src.routers.health_extended import check_redis_health
        
        with patch('src.services.cache.redis_cache.make_redis_cache') as mock_cache:
            mock_redis = Mock()
            mock_redis.get.return_value = None
            mock_redis.set.return_value = True
            mock_redis.delete.return_value = True
            mock_cache.return_value = mock_redis
            
            health = await check_redis_health()
            assert health.status == "healthy"
    
    @pytest.mark.asyncio
    async def test_workflow_health_check(self):
        """Test workflow health check."""
        from src.routers.health_extended import check_workflow_health
        
        with patch('src.workflow.create_guild') as mock_guild:
            mock_guild_obj = Mock()
            mock_guild_obj.workflow = Mock()
            mock_guild.return_value = mock_guild_obj
            
            health = await check_workflow_health()
            assert health.status == "healthy"
            assert health.details["workflow_compiled"] is True


class TestMetrics:
    """Test metrics collection."""
    
    def test_metrics_collection(self):
        """Test Prometheus metrics collection."""
        from src.monitoring.metrics import (
            http_requests_total, http_request_duration,
            workflow_duration, cache_hits_total
        )
        
        # Test HTTP metrics
        http_requests_total.labels(
            method="GET", endpoint="/health", status="200"
        ).inc()
        
        http_request_duration.labels(
            method="GET", endpoint="/health"
        ).observe(0.1)
        
        # Test workflow metrics
        workflow_duration.labels(
            workflow_type="biomarker_analysis"
        ).observe(2.5)
        
        # Test cache metrics
        cache_hits_total.labels(cache_type="redis").inc()
        
        # Verify metrics are created (no errors)
        assert True


class TestBiomarkerNormalization:
    """Test biomarker normalization."""
    
    def test_normalize_glucose(self):
        """Test glucose value normalization."""
        from src.biomarker_normalization import normalize_biomarker
        
        # Test mg/dL to mmol/L conversion
        result = normalize_biomarker("glucose", 100, "mg/dL", "mmol/L")
        assert abs(result - 5.55) < 0.01
        
        # Test same unit conversion
        result = normalize_biomarker("glucose", 100, "mg/dL", "mg/dL")
        assert result == 100
    
    def test_normalize_hba1c(self):
        """Test HbA1c value normalization."""
        from src.biomarker_normalization import normalize_biomarker
        
        # Test percentage to decimal
        result = normalize_biomarker("hba1c", 6.5, "%", "decimal")
        assert abs(result - 0.065) < 0.001
    
    def test_validate_biomarker_range(self):
        """Test biomarker range validation."""
        from src.biomarker_validator import validate_biomarker
        
        # Test normal range
        result = validate_biomarker("glucose", 90, "mg/dL")
        assert result["status"] == "normal"
        
        # Test high value
        result = validate_biomarker("glucose", 150, "mg/dL")
        assert result["status"] == "high"
        
        # Test low value
        result = validate_biomarker("glucose", 60, "mg/dL")
        assert result["status"] == "low"


class TestPDFProcessing:
    """Test PDF processing functionality."""
    
    def test_pdf_text_extraction(self):
        """Test text extraction from PDF."""
        from src.pdf_processor import PDFProcessor
        
        processor = PDFProcessor()
        
        # Mock PDF content
        with patch('PyPDF2.PdfReader') as mock_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = "Sample medical report content"
            mock_pdf = Mock()
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf
            
            text = processor.extract_text("test.pdf")
            assert "Sample medical report content" in text
    
    def test_pdf_metadata_extraction(self):
        """Test metadata extraction from PDF."""
        from src.pdf_processor import PDFProcessor
        
        processor = PDFProcessor()
        
        with patch('PyPDF2.PdfReader') as mock_reader:
            mock_pdf = Mock()
            mock_pdf.metadata = {
                '/Title': 'Medical Report',
                '/Author': 'Dr. Smith',
                '/CreationDate': "D:20240101"
            }
            mock_reader.return_value = mock_pdf
            
            metadata = processor.extract_metadata("test.pdf")
            assert metadata['title'] == 'Medical Report'
            assert metadata['author'] == 'Dr. Smith'


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_environment_config_validation(self):
        """Test environment configuration validation."""
        from src.config import validate_config
        
        # Test valid config
        valid_config = {
            "GROQ_API_KEY": "test-key",
            "REDIS_URL": "redis://localhost:6379",
            "OPENSEARCH_URL": "http://localhost:9200"
        }
        
        assert validate_config(valid_config) is True
    
    def test_missing_required_config(self):
        """Test missing required configuration."""
        from src.config import validate_config
        
        # Test missing API key
        invalid_config = {
            "REDIS_URL": "redis://localhost:6379"
        }
        
        assert validate_config(invalid_config) is False


class TestDatabaseOperations:
    """Test database operations."""
    
    @pytest.mark.asyncio
    async def test_bulk_index_operations(self):
        """Test bulk indexing operations."""
        from src.services.opensearch.client import make_opensearch_client
        
        with patch('src.services.opensearch.client.get_settings') as mock_settings:
            mock_settings.return_value.OPENSEARCH_URL = "http://localhost:9200"
            
            with patch('opensearchpy.OpenSearch') as mock_os:
                mock_client = Mock()
                mock_client.bulk.return_value = {
                    "items": [{"index": {"status": 201}}] * 10
                }
                mock_os.return_value = mock_client
                
                client = make_opensearch_client()
                
                documents = [
                    {"_id": f"doc_{i}", "text": f"Document {i}"}
                    for i in range(10)
                ]
                
                indexed = client.bulk_index(documents)
                assert indexed == 10
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback on errors."""
        from src.repositories.analysis import AnalysisRepository
        
        repo = AnalysisRepository()
        
        with patch.object(repo, 'client') as mock_client:
            # Simulate error during second operation
            mock_client.index.side_effect = [True, Exception("DB Error")]
            
            with pytest.raises(Exception):
                await repo.create_analysis_with_transaction(
                    analysis_id="test_123",
                    patient_data={"test": "data"},
                    results={"result": "test"}
                )


# Integration tests for edge cases
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_biomarker_analysis(self):
        """Test analysis with empty biomarkers."""
        from src.routers.analyze import analyze_structured
        
        payload = {"biomarkers": {}, "patient_context": {}}
        
        with patch('src.routers.analyze.get_ragbot_service') as mock_service:
            mock_service.return_value = None
            
            with pytest.raises(ValueError):
                await analyze_structured(payload)
    
    @pytest.mark.asyncio
    async def test_extreme_values(self):
        """Test handling of extreme biomarker values."""
        from src.biomarker_validator import validate_biomarker
        
        # Test extremely high glucose
        result = validate_biomarker("glucose", 9999, "mg/dL")
        assert result["status"] == "critical"
        
        # Test zero values
        result = validate_biomarker("glucose", 0, "mg/dL")
        assert result["status"] == "critical"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        import asyncio
        from src.routers.health import health_check
        
        # Create many concurrent requests
        tasks = [health_check() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r["status"] == "healthy" for r in results)
    
    def test_unicode_handling(self):
        """Test proper handling of unicode characters."""
        from src.services.extraction.service import ExtractionService
        
        service = ExtractionService(llm=None)
        
        # Test with unicode characters
        text = "Patient姓名: 张三, 年龄: 45岁"
        result = service._extract_context(text)
        
        # Should handle gracefully
        assert isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self):
        """Test proper memory cleanup."""
        from src.services.cache.advanced_cache import MemoryBackend
        
        cache = MemoryBackend(max_size=2)
        
        # Fill cache beyond limit
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")  # Should evict key1
        
        # key1 should be evicted
        result = await cache.get("key1")
        assert result is None
        
        # key3 should exist
        result = await cache.get("key3")
        assert result == "value3"
