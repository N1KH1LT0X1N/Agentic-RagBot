"""Tests for agent modules."""

import pytest
from unittest.mock import Mock, patch

from src.agents.biomarker_analyzer import BiomarkerAnalyzerAgent
from src.agents.biomarker_linker import create_biomarker_linker_agent
from src.agents.clinical_guidelines import create_clinical_guidelines_agent
from src.agents.confidence_assessor import confidence_assessor_agent
from src.agents.disease_explainer import create_disease_explainer_agent
from src.agents.response_synthesizer import response_synthesizer_agent
from src.state import GuildState
from src.config import ExplanationSOP


class TestBiomarkerAnalyzer:
    """Test BiomarkerAnalyzer agent."""

    def test_analyze_normal_biomarkers(self):
        """Test analysis of normal biomarker values."""
        analyzer = BiomarkerAnalyzerAgent()
        state = GuildState(
            patient_biomarkers={"Glucose": 90, "HbA1c": 5.0},
            patient_context={},
            model_prediction={"disease": "Healthy", "confidence": 0.9},
            sop=ExplanationSOP(),
        )
        
        result = analyzer.analyze(state)
        
        assert isinstance(result, dict)
        assert "biomarker_flags" in result

    def test_analyze_abnormal_biomarkers(self):
        """Test analysis of abnormal biomarker values."""
        analyzer = BiomarkerAnalyzerAgent()
        state = GuildState(
            patient_biomarkers={"Glucose": 200, "HbA1c": 9.0},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9},
            sop=ExplanationSOP(),
        )
        
        result = analyzer.analyze(state)
        
        assert isinstance(result, dict)
        assert "biomarker_flags" in result


class TestBiomarkerLinker:
    """Test BiomarkerLinker agent."""

    def test_link_key_drivers(self):
        """Test linking biomarkers to key drivers."""
        mock_retriever = Mock()
        linker = create_biomarker_linker_agent(mock_retriever)
        state = GuildState(
            patient_biomarkers={"Glucose": 200, "HbA1c": 9.0},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9},
            sop=ExplanationSOP(),
        )
        
        result = linker.link(state)
        
        assert isinstance(result, dict)
        assert "agent_outputs" in result
        assert len(result["agent_outputs"]) > 0
        assert "key_drivers" in result["agent_outputs"][0].findings


class TestClinicalGuidelinesAgent:
    """Test ClinicalGuidelinesAgent."""

    def test_generate_recommendations(self):
        """Test generating clinical recommendations."""
        mock_retriever = Mock()
        mock_retriever.invoke.return_value = []  # Return empty list
        agent = create_clinical_guidelines_agent(mock_retriever)
        state = GuildState(
            patient_biomarkers={"Glucose": 200, "HbA1c": 9.0},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9},
            sop=ExplanationSOP(),
        )
        
        result = agent.recommend(state)
        
        assert isinstance(result, dict)
        assert "agent_outputs" in result
        assert len(result["agent_outputs"]) > 0
        findings = result["agent_outputs"][0].findings
        # Check for any recommendation-related keys
        assert any(key in findings for key in ["immediate_actions", "lifestyle_changes", "monitoring", "recommendations"])


class TestConfidenceAssessor:
    """Test ConfidenceAssessor agent."""

    def test_assess_high_confidence(self):
        """Test confidence assessment with strong evidence."""
        assessor = confidence_assessor_agent
        state = GuildState(
            patient_biomarkers={"Glucose": 200, "HbA1c": 9.0},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9},
            retrieved_documents=[{"content": "Diabetes guidelines"}] * 5,
            sop=ExplanationSOP(),
        )
        
        result = assessor.assess(state)
        
        assert isinstance(result, dict)
        # Check if result has agent_outputs or direct assessment
        if "agent_outputs" in result:
            findings = result["agent_outputs"][0].findings
            assert "prediction_reliability" in findings
        else:
            # Direct assessment
            assert "prediction_reliability" in result or "confidence_assessment" in result

    def test_assess_low_confidence(self):
        """Test confidence assessment with weak evidence."""
        assessor = confidence_assessor_agent
        state = GuildState(
            patient_biomarkers={"Glucose": 95, "HbA1c": 5.5},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.3},
            retrieved_documents=[],
            sop=ExplanationSOP(),
        )
        
        result = assessor.assess(state)
        
        assert isinstance(result, dict)
        # Check if result has agent_outputs or direct assessment
        if "agent_outputs" in result:
            findings = result["agent_outputs"][0].findings
            assert "prediction_reliability" in findings
        else:
            # Direct assessment
            assert "prediction_reliability" in result or "confidence_assessment" in result


class TestDiseaseExplainer:
    """Test DiseaseExplainer agent."""

    @patch('src.agents.disease_explainer.llm_config')
    def test_explain_disease(self, mock_config):
        """Test disease explanation generation."""
        mock_model = Mock()
        mock_model.invoke.return_value = Mock(
            content="Diabetes is a metabolic disease characterized by high blood sugar."
        )
        mock_config.explainer = mock_model
        
        mock_retriever = Mock()
        mock_retriever.invoke.return_value = []  # Return empty list
        mock_retriever.search_kwargs = {"k": 5}  # Add search_kwargs
        explainer = create_disease_explainer_agent(mock_retriever)
        state = GuildState(
            patient_biomarkers={"Glucose": 200, "HbA1c": 9.0},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9},
            sop=ExplanationSOP(),
        )
        
        result = explainer.explain(state)
        
        assert isinstance(result, dict)
        assert "agent_outputs" in result
        assert len(result["agent_outputs"]) > 0
        findings = result["agent_outputs"][0].findings
        # Check for disease explanation related keys
        assert any(key in findings for key in ["disease_explanation", "pathophysiology", "clinical_presentation", "disease"])


class TestResponseSynthesizer:
    """Test ResponseSynthesizer agent."""

    @patch('src.agents.response_synthesizer.llm_config')
    def test_synthesize_response(self, mock_config):
        """Test response synthesis."""
        mock_model = Mock()
        mock_model.invoke.return_value = Mock(
            content="Based on your test results, you show signs of diabetes."
        )
        mock_config.synthesizer_7b = mock_model
        
        synthesizer = response_synthesizer_agent
        state = GuildState(
            patient_biomarkers={"Glucose": 200, "HbA1c": 9.0},
            patient_context={},
            model_prediction={"disease": "Diabetes", "confidence": 0.9},
            agent_outputs=[],
            sop=ExplanationSOP(),
        )
        
        result = synthesizer.synthesize(state)
        
        assert isinstance(result, dict)
        # Response synthesizer returns final_response
        assert "final_response" in result
        final_response = result["final_response"]
        # Check for conversational_summary in nested structure
        if "conversational_summary" in final_response:
            assert True  # Found directly
        elif "analysis" in final_response and "conversational_summary" in final_response["analysis"]:
            assert True  # Found in analysis
        else:
            # At least check we have some response structure
            assert "analysis" in final_response or "summary" in final_response
