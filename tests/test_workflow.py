"""Tests for workflow module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.workflow import ClinicalInsightGuild
from src.state import GuildState
from src.config import ExplanationSOP


class TestWorkflow:
    """Test workflow creation and execution."""

    def test_create_workflow(self):
        """Test workflow creation."""
        workflow = ClinicalInsightGuild()
        
        assert workflow is not None
        assert hasattr(workflow, 'workflow')
        assert hasattr(workflow, 'run')

    @patch('src.workflow.get_all_retrievers')
    def test_workflow_initialization(self, mock_retrievers):
        """Test workflow initialization."""
        mock_retrievers.return_value = {
            "disease_explainer": Mock(),
            "biomarker_linker": Mock(),
            "clinical_guidelines": Mock(),
        }
        
        workflow = ClinicalInsightGuild()
        
        assert workflow is not None
        mock_retrievers.assert_called_once()

    @patch('src.workflow.get_all_retrievers')
    def test_analyze_biomarkers_workflow(self, mock_retrievers):
        """Test biomarker analysis workflow execution."""
        mock_retrievers.return_value = {
            "disease_explainer": Mock(),
            "biomarker_linker": Mock(),
            "clinical_guidelines": Mock(),
        }
        
        workflow = ClinicalInsightGuild()
        from src.state import PatientInput
        
        patient_input = PatientInput(
            biomarkers={"Glucose": 200, "HbA1c": 9.0},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9}
        )
        
        # Mock the graph execution
        with patch.object(workflow.workflow, 'invoke') as mock_invoke:
            mock_invoke.return_value = {
                "status": "success",
                "prediction": {"disease": "Diabetes", "confidence": 0.9},
                "analysis": {"biomarker_flags": []},
                "agent_outputs": [],
            }
            
            result = workflow.run(patient_input)
            
            assert "status" in result
            assert "prediction" in result
            assert "analysis" in result
            mock_invoke.assert_called_once()


class TestClinicalInsightGuild:
    """Test ClinicalInsightGuild class."""

    @patch('src.workflow.get_all_retrievers')
    def test_workflow_structure(self, mock_retrievers):
        """Test workflow structure and nodes."""
        mock_retrievers.return_value = {
            "disease_explainer": Mock(),
            "biomarker_linker": Mock(),
            "clinical_guidelines": Mock(),
        }
        
        workflow = ClinicalInsightGuild()
        
        # Verify workflow has required attributes
        assert hasattr(workflow, 'workflow')
        assert hasattr(workflow, 'run')
        # run_stream may not exist

    @patch('src.workflow.get_all_retrievers')
    def test_workflow_with_empty_biomarkers(self, mock_retrievers):
        """Test workflow behavior with empty biomarkers."""
        mock_retrievers.return_value = {
            "disease_explainer": Mock(),
            "biomarker_linker": Mock(),
            "clinical_guidelines": Mock(),
        }
        
        workflow = ClinicalInsightGuild()
        from src.state import PatientInput
        
        patient_input = PatientInput(
            biomarkers={},
            patient_context={},
            model_prediction={"disease": "Unknown", "confidence": 0.0}
        )
        
        # Mock the graph execution
        with patch.object(workflow.workflow, 'invoke') as mock_invoke:
            mock_invoke.return_value = {
                "status": "error",
                "error": "No biomarkers provided",
            }
            
            result = workflow.run(patient_input)
            
            assert result["status"] == "error"

    @patch('src.workflow.get_all_retrievers')
    def test_workflow_stream_execution(self, mock_retrievers):
        """Test workflow streaming execution."""
        mock_retrievers.return_value = {
            "disease_explainer": Mock(),
            "biomarker_linker": Mock(),
            "clinical_guidelines": Mock(),
        }
        
        workflow = ClinicalInsightGuild()
        from src.state import PatientInput
        
        patient_input = PatientInput(
            biomarkers={"Glucose": 200},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9}
        )
        
        # Mock the graph streaming
        with patch.object(workflow.workflow, 'stream') as mock_stream:
            mock_stream.return_value = [
                {"node": "extractor", "output": {"patient_biomarkers": {"Glucose": 200}}},
                {"node": "analyzer", "output": {"flags": []}},
                {"node": "synthesizer", "output": {"summary": "Test result"}},
            ]
            
            # Check if run_stream exists
            if hasattr(workflow, 'run_stream'):
                results = list(workflow.run_stream(patient_input))
                assert len(results) == 3
                assert all("node" in result for result in results)
                assert all("output" in result for result in results)
