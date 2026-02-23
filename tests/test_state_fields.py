from src.state import GuildState


def test_state_has_biomarker_analysis_field():
    required_fields = {"biomarker_analysis", "biomarker_flags", "safety_alerts"}
    assert required_fields.issubset(GuildState.__annotations__.keys())
