import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from app.services.extraction import predict_disease_simple


def test_low_confidence_returns_undetermined():
    result = predict_disease_simple({})
    assert result["confidence"] == 0.0
    assert result["disease"] == "Undetermined"
