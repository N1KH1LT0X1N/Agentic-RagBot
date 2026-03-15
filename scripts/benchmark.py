"""
Performance benchmarking suite for MediGuard AI.
Measures and tracks performance metrics across different components.
"""

import asyncio
import time
import statistics
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from src.workflow import create_guild
from src.state import PatientInput


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    metric_name: str
    value: float
    unit: str
    samples: int
    min_value: float
    max_value: float
    mean: float
    median: float
    p95: float
    p99: float


class PerformanceBenchmark:
    """Performance benchmarking suite."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[BenchmarkResult] = []
        
    async def benchmark_api_endpoints(self, concurrent_users: int = 10, requests_per_user: int = 5):
        """Benchmark API endpoints under load."""
        print(f"\n🚀 Benchmarking API endpoints with {concurrent_users} concurrent users...")
        
        endpoints = [
            ("/health", "GET", {}),
            ("/analyze/structured", "POST", {
                "biomarkers": {"Glucose": 140, "HbA1c": 10.0},
                "patient_context": {"age": 45, "gender": "male"}
            }),
            ("/ask", "POST", {
                "question": "What are the symptoms of diabetes?",
                "context": {"patient_age": 45}
            }),
            ("/search", "POST", {
                "query": "diabetes management",
                "top_k": 5
            })
        ]
        
        for endpoint, method, payload in endpoints:
            await self._benchmark_endpoint(endpoint, method, payload, concurrent_users, requests_per_user)
    
    async def _benchmark_endpoint(self, endpoint: str, method: str, payload: Dict, 
                                 concurrent_users: int, requests_per_user: int):
        """Benchmark a single endpoint."""
        url = f"{self.base_url}{endpoint}"
        response_times = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            
            for _ in range(concurrent_users):
                for _ in range(requests_per_user):
                    if method == "GET":
                        task = self._make_request(client, "GET", url)
                    else:
                        task = self._make_request(client, "POST", url, json=payload)
                    tasks.append(task)
            
            # Execute all requests
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Collect response times
            for response in responses:
                if isinstance(response, Exception):
                    print(f"Request failed: {response}")
                else:
                    response_times.append(response)
        
        # Calculate metrics
        if response_times:
            result = BenchmarkResult(
                metric_name=f"{method} {endpoint}",
                value=statistics.mean(response_times),
                unit="ms",
                samples=len(response_times),
                min_value=min(response_times),
                max_value=max(response_times),
                mean=statistics.mean(response_times),
                median=statistics.median(response_times),
                p95=self._percentile(response_times, 95),
                p99=self._percentile(response_times, 99)
            )
            self.results.append(result)
            
            # Print results
            print(f"\n📊 {method} {endpoint}:")
            print(f"   Requests: {result.samples}")
            print(f"   Average: {result.mean:.2f}ms")
            print(f"   Median: {result.median:.2f}ms")
            print(f"   P95: {result.p95:.2f}ms")
            print(f"   P99: {result.p99:.2f}ms")
            print(f"   Throughput: {result.samples / total_time:.2f} req/s")
    
    async def _make_request(self, client: httpx.AsyncClient, method: str, url: str, json: Dict = None) -> float:
        """Make a single request and return response time."""
        start_time = time.time()
        try:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=json)
            response.raise_for_status()
            return (time.time() - start_time) * 1000  # Convert to ms
        except Exception as e:
            print(f"Request error: {e}")
            return float('inf')
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    async def benchmark_workflow_performance(self, iterations: int = 10):
        """Benchmark the workflow performance."""
        print(f"\n⚙️ Benchmarking workflow performance ({iterations} iterations)...")
        
        guild = create_guild()
        response_times = []
        
        for i in range(iterations):
            patient_input = PatientInput(
                biomarkers={"Glucose": 140, "HbA1c": 10.0, "Hemoglobin": 11.5},
                patient_context={"age": 45, "gender": "male", "symptoms": ["fatigue"]},
                model_prediction={"disease": "Diabetes", "confidence": 0.9}
            )
            
            start_time = time.time()
            try:
                result = await guild.workflow.ainvoke(patient_input)
                if "final_response" in result:
                    response_times.append((time.time() - start_time) * 1000)
            except Exception as e:
                print(f"Iteration {i} failed: {e}")
        
        if response_times:
            result = BenchmarkResult(
                metric_name="Workflow Execution",
                value=statistics.mean(response_times),
                unit="ms",
                samples=len(response_times),
                min_value=min(response_times),
                max_value=max(response_times),
                mean=statistics.mean(response_times),
                median=statistics.median(response_times),
                p95=self._percentile(response_times, 95),
                p99=self._percentile(response_times, 99)
            )
            self.results.append(result)
            
            print(f"\n📊 Workflow Performance:")
            print(f"   Average: {result.mean:.2f}ms")
            print(f"   Median: {result.median:.2f}ms")
            print(f"   P95: {result.p95:.2f}ms")
    
    def benchmark_memory_usage(self):
        """Benchmark memory usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        print(f"\n💾 Memory Usage:")
        print(f"   RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
        print(f"   VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
        print(f"   % Memory: {process.memory_percent():.2f}%")
        
        # Track memory over time
        memory_samples = []
        for _ in range(10):
            memory_samples.append(process.memory_info().rss / 1024 / 1024)
            time.sleep(1)
        
        print(f"   Memory range: {min(memory_samples):.2f} - {max(memory_samples):.2f} MB")
    
    async def benchmark_database_queries(self):
        """Benchmark database query performance."""
        print(f"\n🗄️ Benchmarking database queries...")
        
        # Test OpenSearch query performance
        try:
            from src.services.opensearch.client import make_opensearch_client
            client = make_opensearch_client()
            
            query_times = []
            for _ in range(10):
                start_time = time.time()
                results = client.search(
                    index="medical_chunks",
                    body={"query": {"match": {"text": "diabetes"}}, "size": 10}
                )
                query_times.append((time.time() - start_time) * 1000)
            
            if query_times:
                result = BenchmarkResult(
                    metric_name="OpenSearch Query",
                    value=statistics.mean(query_times),
                    unit="ms",
                    samples=len(query_times),
                    min_value=min(query_times),
                    max_value=max(query_times),
                    mean=statistics.mean(query_times),
                    median=statistics.median(query_times),
                    p95=self._percentile(query_times, 95),
                    p99=self._percentile(query_times, 99)
                )
                self.results.append(result)
                
                print(f"\n📊 OpenSearch Query Performance:")
                print(f"   Average: {result.mean:.2f}ms")
                print(f"   P95: {result.p95:.2f}ms")
                
        except Exception as e:
            print(f"   OpenSearch benchmark failed: {e}")
        
        # Test Redis cache performance
        try:
            from src.services.cache.redis_cache import make_redis_cache
            cache = make_redis_cache()
            
            cache_times = []
            test_key = "benchmark_test"
            test_value = json.dumps({"test": "data"})
            
            # Benchmark writes
            for _ in range(100):
                start_time = time.time()
                cache.set(test_key, test_value, ttl=60)
                cache_times.append((time.time() - start_time) * 1000)
            
            # Benchmark reads
            read_times = []
            for _ in range(100):
                start_time = time.time()
                cache.get(test_key)
                read_times.append((time.time() - start_time) * 1000)
            
            # Clean up
            cache.delete(test_key)
            
            write_result = BenchmarkResult(
                metric_name="Redis Write",
                value=statistics.mean(cache_times),
                unit="ms",
                samples=len(cache_times),
                min_value=min(cache_times),
                max_value=max(cache_times),
                mean=statistics.mean(cache_times),
                median=statistics.median(cache_times),
                p95=self._percentile(cache_times, 95),
                p99=self._percentile(cache_times, 99)
            )
            self.results.append(write_result)
            
            read_result = BenchmarkResult(
                metric_name="Redis Read",
                value=statistics.mean(read_times),
                unit="ms",
                samples=len(read_times),
                min_value=min(read_times),
                max_value=max(read_times),
                mean=statistics.mean(read_times),
                median=statistics.median(read_times),
                p95=self._percentile(read_times, 95),
                p99=self._percentile(read_times, 99)
            )
            self.results.append(read_result)
            
            print(f"\n📊 Redis Performance:")
            print(f"   Write - Average: {write_result.mean:.2f}ms, P95: {write_result.p95:.2f}ms")
            print(f"   Read  - Average: {read_result.mean:.2f}ms, P95: {read_result.p95:.2f}ms")
            
        except Exception as e:
            print(f"   Redis benchmark failed: {e}")
    
    def save_results(self, filename: str = "benchmark_results.json"):
        """Save benchmark results to file."""
        results_data = []
        for result in self.results:
            results_data.append({
                "metric": result.metric_name,
                "value": result.value,
                "unit": result.unit,
                "samples": result.samples,
                "min": result.min_value,
                "max": result.max_value,
                "mean": result.mean,
                "median": result.median,
                "p95": result.p95,
                "p99": result.p99
            })
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": time.time(),
                "results": results_data
            }, f, indent=2)
        
        print(f"\n💾 Results saved to {filename}")
    
    def print_summary(self):
        """Print a summary of all benchmark results."""
        print("\n" + "="*70)
        print("📊 PERFORMANCE BENCHMARK SUMMARY")
        print("="*70)
        
        for result in self.results:
            print(f"\n{result.metric_name}:")
            print(f"   Average: {result.mean:.2f}{result.unit}")
            print(f"   Range: {result.min_value:.2f} - {result.max_value:.2f}{result.unit}")
            print(f"   Samples: {result.samples}")


async def main():
    """Run the complete benchmark suite."""
    print("🚀 Starting MediGuard AI Performance Benchmark Suite")
    print("="*70)
    
    benchmark = PerformanceBenchmark()
    
    # Run all benchmarks
    await benchmark.benchmark_api_endpoints(concurrent_users=5, requests_per_user=3)
    await benchmark.benchmark_workflow_performance(iterations=5)
    benchmark.benchmark_memory_usage()
    await benchmark.benchmark_database_queries()
    
    # Save and display results
    benchmark.save_results()
    benchmark.print_summary()
    
    print("\n✅ Benchmark suite completed!")


if __name__ == "__main__":
    asyncio.run(main())
