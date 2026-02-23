from src.biomarker_normalization import normalize_biomarker_name


def test_normalizes_common_aliases():
    assert normalize_biomarker_name("ldl") == "LDL Cholesterol"
    assert normalize_biomarker_name("wbc") == "White Blood Cells"
    assert normalize_biomarker_name("systolic bp") == "Systolic Blood Pressure"
