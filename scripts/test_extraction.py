"""
Quick test to verify biomarker extraction is working
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.chat import extract_biomarkers, predict_disease_llm

# Test cases
test_inputs = [
    "My glucose is 140 and HbA1c is 7.5",
    "hemoglobin 10.5, RBC 3.8, MCV 78",
    "glucose=185, HbA1c=8.2, cholesterol=235, triglycerides=210, HDL=38",
]

print("="*70)
print("BIOMARKER EXTRACTION TEST")
print("="*70)

for i, test_input in enumerate(test_inputs, 1):
    print(f"\n[Test {i}] Input: '{test_input}'")
    print("-"*70)
    
    biomarkers, context = extract_biomarkers(test_input)
    
    if biomarkers:
        print(f"✅ SUCCESS: Found {len(biomarkers)} biomarkers")
        for name, value in biomarkers.items():
            print(f"   - {name}: {value}")
        
        if context:
            print(f"   Context: {context}")
        
        # Test prediction
        print("\n   Testing prediction...")
        prediction = predict_disease_llm(biomarkers, context)
        print(f"   Predicted: {prediction['disease']} ({prediction['confidence']:.0%})")
        
    else:
        print(f"❌ FAILED: No biomarkers extracted")
    
    print()

print("="*70)
print("TEST COMPLETE")
print("="*70)
