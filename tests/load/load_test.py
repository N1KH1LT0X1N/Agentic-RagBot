"""
Load testing suite for MediGuard AI using Locust.
Tests API endpoints under various load conditions.
"""

from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
import json
import random
import time
from datetime import datetime


class MediGuardUser(HttpUser):
    """Simulated user behavior for load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        # Check if API is available
        response = self.client.get("/health")
        if response.status_code != 200:
            print("API not available for load testing")
            exit(1)
        
        print(f"User started: {self.environment.parsed_options.host}")
    
    @task(3)
    def analyze_structured_biomarkers(self):
        """Analyze structured biomarkers - most common operation."""
        payload = {
            "biomarkers": {
                "Glucose": random.randint(70, 200),
                "HbA1c": round(random.uniform(4.0, 12.0), 1),
                "Hemoglobin": random.randint(10, 16),
                "MCV": random.randint(70, 100)
            },
            "patient_context": {
                "age": random.randint(18, 80),
                "gender": random.choice(["male", "female"]),
                "symptoms": random.sample(["fatigue", "thirst", "frequent_urination", "blurred_vision"], k=random.randint(1, 3))
            }
        }
        
        with self.client.post(
            "/analyze/structured",
            json=payload,
            catch_response=True,
            name="/analyze/structured"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "analysis" not in data:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def ask_medical_question(self):
        """Ask medical questions."""
        questions = [
            "What are the symptoms of diabetes?",
            "How is hypertension diagnosed?",
            "What causes high cholesterol?",
            "What are the complications of diabetes?",
            "How to manage blood pressure?",
            "What is a normal glucose level?",
            "What foods lower blood sugar?",
            "How often should I check my blood pressure?",
            "What is prediabetes?",
            "Can diabetes be reversed?"
        ]
        
        payload = {
            "question": random.choice(questions),
            "context": {
                "patient_age": random.randint(18, 80),
                "gender": random.choice(["male", "female"])
            }
        }
        
        with self.client.post(
            "/ask",
            json=payload,
            catch_response=True,
            name="/ask"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "answer" not in data:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def search_knowledge_base(self):
        """Search the knowledge base."""
        queries = [
            "diabetes management guidelines",
            "hypertension treatment",
            "cholesterol levels",
            "blood sugar monitoring",
            "heart disease prevention",
            "kidney disease diabetes",
            "metabolic syndrome",
            "insulin resistance",
            "type 2 diabetes",
            "cardiovascular risk"
        ]
        
        payload = {
            "query": random.choice(queries),
            "top_k": random.randint(5, 10)
        }
        
        with self.client.post(
            "/search",
            json=payload,
            catch_response=True,
            name="/search"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "results" not in data:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def analyze_natural_language(self):
        """Analyze natural language input."""
        texts = [
            "My blood sugar is 150 and I feel very thirsty lately. I'm a 45-year-old male.",
            "Recent lab work shows HbA1c of 8.5%. I have been feeling tired and urinating frequently.",
            "Doctor said my cholesterol is high at 250. What should I do? I'm 60 years old.",
            "Fasting glucose was 130 this morning. Is that bad? I'm 30 and female.",
            "Blood pressure reading was 140/90. Should I be worried? I'm 50 years old."
        ]
        
        payload = {
            "text": random.choice(texts),
            "extract_biomarkers": True
        }
        
        with self.client.post(
            "/analyze/natural",
            json=payload,
            catch_response=True,
            name="/analyze/natural"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "analysis" not in data:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(5)
    def health_check(self):
        """Lightweight health check - very frequent."""
        self.client.get("/health", name="/health")


class StressTestUser(HttpUser):
    """User for stress testing - higher intensity."""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    @task(10)
    def rapid_health_checks(self):
        """Rapid health checks to test basic connectivity."""
        self.client.get("/health", name="/health (stress)")
    
    @task(5)
    def rapid_analysis(self):
        """Quick analysis requests."""
        payload = {
            "biomarkers": {
                "Glucose": 100,
                "HbA1c": 6.0
            },
            "patient_context": {
                "age": 40,
                "gender": "male"
            }
        }
        
        self.client.post("/analyze/structured", json=payload, name="/analyze/structured (stress)")


class SpikeTestUser(HttpUser):
    """User for spike testing - sudden bursts."""
    
    wait_time = between(0.01, 0.1)  # Almost no wait
    
    @task
    def spike_requests(self):
        """Generate spike in traffic."""
        payload = {
            "question": "What is diabetes?",
            "context": {"patient_age": 40}
        }
        self.client.post("/ask", json=payload, name="/ask (spike)")


# Custom event handlers for reporting
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Custom request handler for logging."""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif response_time > 5000:  # Log slow requests
        print(f"Slow request: {name} - {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print(f"\nLoad test started at {datetime.now()}")
    print(f"Target: {environment.host}")
    print(f"Users: {environment.parsed_options.num_users if hasattr(environment.parsed_options, 'num_users') else 'default'}")
    print(f"Hatch rate: {environment.parsed_options.hatch_rate if hasattr(environment.parsed_options, 'hatch_rate') else 'default'}")
    print("-" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("-" * 50)
    print(f"Load test completed at {datetime.now()}")
    
    # Print summary statistics
    stats = environment.stats
    print(f"\nTest Summary:")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {(stats.total.num_failures / stats.total.num_requests * 100):.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Median response time: {stats.total.median_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")


# Test scenarios
def run_basic_load_test():
    """Run basic load test with moderate load."""
    from locust import run_single_user
    
    print("Running basic load test...")
    MediGuardUser.host = "http://localhost:8000"
    run_single_user(MediGuardUser)


def run_stress_test():
    """Run stress test with high load."""
    from locust import run_single_user
    
    print("Running stress test...")
    StressTestUser.host = "http://localhost:8000"
    run_single_user(StressTestUser)


def run_spike_test():
    """Run spike test with burst load."""
    from locust import run_single_user
    
    print("Running spike test...")
    SpikeTestUser.host = "http://localhost:8000"
    run_single_user(SpikeTestUser)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        
        if test_type == "basic":
            run_basic_load_test()
        elif test_type == "stress":
            run_stress_test()
        elif test_type == "spike":
            run_spike_test()
        else:
            print("Usage: python load_test.py [basic|stress|spike]")
    else:
        print("Usage: python load_test.py [basic|stress|spike]")
        print("\nFor distributed testing, use:")
        print("locust -f load_test.py --host=http://localhost:8000")
