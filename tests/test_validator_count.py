from src.biomarker_validator import BiomarkerValidator


def test_expected_biomarker_count_is_reference_size():
    validator = BiomarkerValidator()
    assert validator.expected_biomarker_count() == len(validator.references)
