from api.app.services.extraction import _parse_llm_json


def test_parse_llm_json_recovers_embedded_object():
    content = "Here is your JSON:\n```json\n{\"biomarkers\": {\"Glucose\": 140}}\n```"
    parsed = _parse_llm_json(content)
    assert parsed["biomarkers"]["Glucose"] == 140
