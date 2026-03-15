"""
End-to-end integration tests for the complete workflow.
Tests the full pipeline from input to output with real services.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from src.main import create_app
from src.state import PatientInput
from src.workflow import create_guild


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def guild(self):
        """Create workflow guild for testing."""
        return create_guild()

    def test_complete_biomarker_analysis_workflow(self, client):
        """Test the complete biomarker analysis workflow via API."""
        # Input data
        payload = {
            "biomarkers": {
                "Glucose": 140,
                "HbA1c": 10.0,
                "Hemoglobin": 11.5,
                "MCV": 75
            },
            "patient_context": {
                "age": 45,
                "gender": "male",
                "symptoms": ["fatigue", "thirst"]
            }
        }

        # Make API call
        response = client.post("/analyze/structured", json=payload)
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "primary_findings" in data["analysis"]
        assert "critical_alerts" in data["analysis"]
        assert "recommendations" in data["analysis"]
        assert "biomarker_flags" in data["analysis"]
        
        # Verify content
        findings = data["analysis"]["primary_findings"]
        assert len(findings) > 0
        assert all("condition" in f for f in findings)
        assert all("confidence" in f for f in findings)
        
        # Verify biomarker flags
        flags = data["analysis"]["biomarker_flags"]
        assert len(flags) > 0
        glucose_flag = next((f for f in flags if f["name"] == "Glucose"), None)
        assert glucose_flag is not None
        assert glucose_flag["value"] == 140
        assert glucose_flag["status"] == "high"

    def test_medical_qa_workflow(self, client):
        """Test the medical Q&A workflow via API."""
        payload = {
            "question": "What are the symptoms of diabetes?",
            "context": {
                "patient_age": 45,
                "gender": "male"
            }
        }

        response = client.post("/ask", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "content" in data["answer"]
        assert "sources" in data["answer"]
        
        # Verify answer content
        assert len(data["answer"]["content"]) > 100
        assert "diabetes" in data["answer"]["content"].lower()
        
        # Verify sources
        sources = data["answer"]["sources"]
        assert len(sources) > 0
        assert all("title" in s for s in sources)
        assert all("snippet" in s for s in sources)

    def test_knowledge_base_search_workflow(self, client):
        """Test the knowledge base search workflow."""
        payload = {
            "query": "diabetes management guidelines",
            "top_k": 5
        }

        response = client.post("/search", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_found" in data
        
        results = data["results"]
        assert len(results) > 0
        assert all("title" in r for r in results)
        assert all("score" in r for r in results)
        
        # Verify relevance
        assert any("diabetes" in r["title"].lower() for r in results)

    @pytest.mark.asyncio
    async def test_workflow_state_transitions(self, guild):
        """Test state transitions through the workflow."""
        # Create patient input
        patient_input = PatientInput(
            biomarkers={"Glucose": 140, "HbA1c": 10.0},
            patient_context={"age": 45, "gender": "male"},
            model_prediction={"disease": "Diabetes", "confidence": 0.9}
        )

        # Run workflow
        with patch('src.workflow.logger'):
            result = await guild.workflow.ainvoke(patient_input)
        
        # Verify final state
        assert "final_response" in result
        assert "agent_outputs" in result
        
        # Verify all agents executed
        agents = ["biomarker_analyzer", "disease_explainer", "biomarker_linker",
                 "clinical_guidelines", "confidence_assessor", "response_synthesizer"]
        
        for agent in agents:
            assert agent in result["agent_outputs"]
            assert result["agent_outputs"][agent] is not None

    def test_error_handling_workflow(self, client):
        """Test error handling in workflows."""
        # Test with invalid biomarkers
        payload = {
            "biomarkers": {
                "Glucose": "invalid",  # Should be number
                "HbA1c": 10.0
            }
        }

        response = client.post("/analyze/structured", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data or "details" in data

    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        import threading
        import time

        results = []
        
        def make_request():
            payload = {
                "biomarkers": {"Glucose": 120, "HbA1c": 6.5},
                "patient_context": {"age": 30, "gender": "female"}
            }
            response = client.post("/analyze/structured", json=payload)
            results.append(response.status_code)
        
        # Create 5 concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        assert len(results) == 5
        assert all(status == 200 for status in results)

    @pytest.mark.asyncio
    async def test_streaming_response(self):
        """Test streaming response for real-time interaction."""
        from fastapi.testclient import TestClient
        from src.main import create_app
        
        app = create_app()
        client = TestClient(app)
        
        payload = {
            "question": "Explain what HbA1c means",
            "stream": True
        }
        
        with client.stream("POST", "/ask/stream", json=payload) as response:
            assert response.status_code == 200
            
            # Collect streaming chunks
            chunks = []
            for line in response.iter_lines():
                if line:
                    chunks.append(line.decode())
            
            # Verify streaming format
            assert len(chunks) > 0
            assert any("start" in chunk for chunk in chunks)
            assert any("token" in chunk for chunk in chunks)
            assert any("end" in chunk for chunk in chunks)

    def test_natural_language_extraction(self, client):
        """Test biomarker extraction from natural language."""
        payload = {
            "text": "My blood test shows glucose 140 mg/dL, HbA1c is 10%, and hemoglobin is 11.5 g/dL. I'm a 45-year-old male.",
            "extract_biomarkers": True
        }

        response = client.post("/analyze/natural", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "extracted_data" in data
        assert "analysis" in data
        
        # Verify extraction
        extracted = data["extracted_data"]
        assert "biomarkers" in extracted
        assert extracted["biomarkers"].get("Glucose") == 140
        assert extracted["biomarkers"].get("HbA1c") == 10.0
        assert extracted["biomarkers"].get("Hemoglobin") == 11.5
        
        # Verify patient context
        assert "patient_context" in extracted
        assert extracted["patient_context"].get("age") == 45
        assert extracted["patient_context"].get("gender") == "male"

    def test_confidence_scoring_consistency(self, client):
        """Test confidence scoring is consistent across runs."""
        payload = {
            "biomarkers": {
                "Glucose": 140,
                "HbA1c": 10.0
            },
            "patient_context": {
                "age": 45,
                "gender": "male"
            }
        }

        # Make multiple requests
        responses = []
        for _ in range(3):
            response = client.post("/analyze/structured", json=payload)
            assert response.status_code == 200
            responses.append(response.json())
        
        # Verify consistency in findings
        findings_0 = responses[0]["analysis"]["primary_findings"]
        for i in range(1, 3):
            findings_i = responses[i]["analysis"]["primary_findings"]
            assert len(findings_0) == len(findings_i)
            
            # Same conditions should be detected
            conditions_0 = {f["condition"] for f in findings_0}
            conditions_i = {f["condition"] for f in findings_i}
            assert conditions_0 == conditions_i

    def test_service_degradation(self, client):
        """Test graceful degradation when services are unavailable."""
        # This test would require mocking service unavailability
        # For now, we'll test the health endpoint shows service status
        
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data
        
        # Services should report their status
        services = data["services"]
        expected_services = ["opensearch", "redis", "llm"]
        for service in expected_services:
            assert service in services
            assert services[service] in ["connected", "unavailable"]

    def test_input_validation_edge_cases(self, client):
        """Test input validation with edge cases."""
        test_cases = [
            # Empty biomarkers
            {"biomarkers": {}, "patient_context": {"age": 30}},
            # Extreme values
            {"biomarkers": {"Glucose": 9999, "HbA1c": 99.9}},
            # Negative values
            {"biomarkers": {"Glucose": -10, "HbA1c": 5.0}},
            # Zero values
            {"biomarkers": {"Glucose": 0, "HbA1c": 0}},
            # Very long context
            {"biomarkers": {"Glucose": 100}, 
             "patient_context": {"notes": "x" * 10000}}
        ]
        
        for payload in test_cases:
            response = client.post("/analyze/structured", json=payload)
            # Should either succeed or fail gracefully
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert "analysis" in data

    @pytest.mark.asyncio
    async def test_workflow_performance_metrics(self, guild):
        """Test workflow performance and collect metrics."""
        import time
        
        patient_input = PatientInput(
            biomarkers={"Glucose": 140, "HbA1c": 10.0},
            patient_context={"age": 45, "gender": "male"}
        )
        
        # Measure execution time
        start_time = time.time()
        
        with patch('src.workflow.logger'):
            result = await guild.workflow.ainvoke(patient_input)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify performance
        assert execution_time < 10.0  # Should complete within 10 seconds
        assert "final_response" in result
        
        # Check for timing information in metadata if available
        if "metadata" in result:
            assert "processing_time" in result["metadata"]

    def test_cross_service_communication(self, client):
        """Test communication between different services."""
        # First, search for information
        search_payload = {
            "query": "diabetes complications",
            "top_k": 3
        }
        
        search_response = client.post("/search", json=search_payload)
        assert search_response.status_code == 200
        
        # Then use that information in a question
        if search_response.json()["results"]:
            first_result = search_response.json()["results"][0]
            question_payload = {
                "question": f"Based on {first_result['title']}, what are the main complications?"
            }
            
            answer_response = client.post("/ask", json=question_payload)
            assert answer_response.status_code == 200
            
            # Verify the answer references relevant information
            answer = answer_response.json()["answer"]["content"]
            assert len(answer) > 50
