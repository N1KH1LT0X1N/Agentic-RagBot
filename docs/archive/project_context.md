# MediGuard AI RAG-Helper - Project Context

## 🎯 Project Overview
**MediGuard AI RAG-Helper** is a self-improving multi-agent RAG system that provides explainable clinical predictions for patient self-assessment. The system takes raw blood test biomarker values and a disease prediction from a pre-trained ML model, then generates comprehensive, evidence-backed explanations using medical literature.

---

## 📊 System Scope

### **Diseases Covered** (5 conditions)
1. Anemia
2. Diabetes  
3. Thrombocytopenia
4. Thalassemia
5. Heart Disease

### **Input Biomarkers** (24 clinical parameters)
1. Glucose
2. Cholesterol
3. Hemoglobin
4. Platelets
5. White Blood Cells
6. Red Blood Cells
7. Hematocrit
8. Mean Corpuscular Volume (MCV)
9. Mean Corpuscular Hemoglobin (MCH)
10. Mean Corpuscular Hemoglobin Concentration (MCHC)
11. Insulin
12. BMI
13. Systolic Blood Pressure
14. Diastolic Blood Pressure
15. Triglycerides
16. HbA1c
17. LDL Cholesterol
18. HDL Cholesterol
19. ALT (Alanine Aminotransferase)
20. AST (Aspartate Aminotransferase)
21. Heart Rate
22. Creatinine
23. Troponin
24. C-reactive Protein

### **Biomarker Reference Ranges**

| Biomarker | Normal Range (Adults) | Unit | Critical Values |
|-----------|----------------------|------|-----------------|
| **Glucose (Fasting)** | 70-100 | mg/dL | <70 (hypoglycemia), >126 (diabetes) |
| **Cholesterol (Total)** | <200 | mg/dL | >240 (high risk) |
| **Hemoglobin** | M: 13.5-17.5, F: 12.0-15.5 | g/dL | <7 (severe anemia), >18 (polycythemia) |
| **Platelets** | 150,000-400,000 | cells/μL | <50,000 (critical), >1,000,000 (thrombocytosis) |
| **White Blood Cells** | 4,000-11,000 | cells/μL | <2,000 (critical), >30,000 (leukemia risk) |
| **Red Blood Cells** | M: 4.5-5.9, F: 4.0-5.2 | million/μL | <3.0 (severe anemia) |
| **Hematocrit** | M: 38.8-50.0, F: 34.9-44.5 | % | <25 (severe anemia), >60 (polycythemia) |
| **MCV** | 80-100 | fL | <80 (microcytic), >100 (macrocytic) |
| **MCH** | 27-33 | pg | <27 (hypochromic) |
| **MCHC** | 32-36 | g/dL | <32 (hypochromic) |
| **Insulin (Fasting)** | 2.6-24.9 | μIU/mL | >25 (insulin resistance) |
| **BMI** | 18.5-24.9 | kg/m² | <18.5 (underweight), >30 (obese) |
| **Systolic BP** | 90-120 | mmHg | <90 (hypotension), >140 (hypertension) |
| **Diastolic BP** | 60-80 | mmHg | <60 (hypotension), >90 (hypertension) |
| **Triglycerides** | <150 | mg/dL | >500 (pancreatitis risk) |
| **HbA1c** | <5.7 | % | 5.7-6.4 (prediabetes), ≥6.5 (diabetes) |
| **LDL Cholesterol** | <100 | mg/dL | >190 (very high risk) |
| **HDL Cholesterol** | M: >40, F: >50 | mg/dL | <40 (cardiac risk) |
| **ALT** | 7-56 | U/L | >200 (liver damage) |
| **AST** | 10-40 | U/L | >200 (liver/heart damage) |
| **Heart Rate** | 60-100 | bpm | <50 (bradycardia), >120 (tachycardia) |
| **Creatinine** | M: 0.7-1.3, F: 0.6-1.1 | mg/dL | >3.0 (kidney failure) |
| **Troponin** | <0.04 | ng/mL | >0.04 (myocardial injury) |
| **C-reactive Protein** | <3.0 | mg/L | >10 (acute inflammation) |

---

## 🏗️ System Architecture

### **Two-Loop Design** (Adapted from Clinical Trials Architect)

#### **INNER LOOP: Clinical Insight Guild**
Multi-agent RAG pipeline that generates explainable clinical reports.

**Agents:**
1. **Planner Agent** - Creates task execution plan
2. **Biomarker Analyzer Agent** - Validates values against reference ranges, flags anomalies
3. **Disease Explainer Agent** - Retrieves disease pathophysiology from medical PDFs
4. **Biomarker-Disease Linker Agent** - Connects specific biomarker values to predicted disease
5. **Clinical Guidelines Agent** - Retrieves evidence-based recommendations from PDFs
6. **Confidence Assessor Agent** - Evaluates prediction reliability and evidence strength
7. **Response Synthesizer Agent** - Compiles structured JSON output

#### **OUTER LOOP: Clinical Explanation Director**
Meta-learning system that improves explanation quality over time.

**Components:**
- **Performance Diagnostician** - Analyzes which dimensions need improvement
- **SOP Architect** - Evolves explanation strategies (prompts, retrieval params, agent configs)
- **Gene Pool** - Tracks all SOP versions and their performance

---

## 📚 Knowledge Infrastructure

### **Data Sources**

1. **Medical PDF Documents** (User-provided)
   - Disease-specific medical literature
   - Clinical guidelines
   - Biomarker interpretation guides
   - Treatment protocols

2. **Biomarker Reference Database** (Structured)
   - Normal ranges by age/gender
   - Critical value thresholds
   - Unit conversions
   - Clinical significance flags

3. **Disease-Biomarker Associations** (Derived from PDFs)
   - Which biomarkers are diagnostic for each disease
   - Pathophysiological mechanisms
   - Differential diagnosis criteria

### **Storage & Indexing**

| Data Type | Storage | Access Method |
|-----------|---------|---------------|
| Medical PDFs | FAISS Vector Store | Semantic search (embeddings) |
| Reference Ranges | DuckDB/JSON | SQL queries / Dict lookup |
| Disease Mappings | Python Dict/JSON | Key-value retrieval |

---

## 🔄 Workflow

### **Patient Input**
```json
{
  "biomarkers": {
    "glucose": 185,
    "hba1c": 8.2,
    "hemoglobin": 11.5,
    "platelets": 220000,
    // ... all 24 biomarkers
  },
  "model_prediction": {
    "disease": "Diabetes",
    "confidence": 0.89,
    "probabilities": {
      "Diabetes": 0.89,
      "Heart Disease": 0.06,
      "Anemia": 0.03,
      "Thalassemia": 0.01,
      "Thrombocytopenia": 0.01
    }
  }
}
```

### **System Processing**
1. **Biomarker Validation** - Check all values against reference ranges
2. **RAG Retrieval** - Query PDFs for disease mechanism + biomarker significance
3. **Explanation Generation** - Link biomarkers to prediction with evidence
4. **Safety Checks** - Flag critical values, missing data, low confidence
5. **Recommendation Synthesis** - Provide actionable next steps from guidelines

### **Output Structure**
```json
{
  "patient_summary": {
    "biomarker_flags": [...],  // Out-of-range values with warnings
    "overall_risk_profile": "High metabolic risk"
  },
  "prediction_explanation": {
    "primary_disease": "Diabetes",
    "confidence": 0.89,
    "key_drivers": [
      {
        "biomarker": "HbA1c",
        "value": 8.2,
        "contribution": "45%",
        "explanation": "HbA1c of 8.2% indicates poor glycemic control...",
        "evidence": "ADA Guidelines 2024, Section 2.3: 'HbA1c ≥6.5% diagnostic'"
      }
    ],
    "mechanism_summary": "Type 2 Diabetes results from insulin resistance...",
    "pdf_references": ["diabetes_pathophysiology.pdf p.15", ...]
  },
  "clinical_recommendations": {
    "immediate_actions": ["Repeat fasting glucose", "Consult physician"],
    "lifestyle_changes": ["Reduce sugar intake", "Exercise 30min daily"],
    "monitoring": ["Check HbA1c every 3 months"],
    "guideline_citations": ["ADA Standards of Care 2024"]
  },
  "confidence_assessment": {
    "prediction_reliability": "HIGH",
    "evidence_strength": "STRONG",
    "limitations": ["Missing lipid panel data"],
    "recommendation": "High confidence diagnosis; seek medical consultation"
  },
  "safety_alerts": [
    {
      "severity": "HIGH",
      "biomarker": "Glucose",
      "message": "Fasting glucose 185 mg/dL significantly elevated",
      "action": "Urgent physician consultation recommended"
    }
  ]
}
```

---

## 🎯 Multi-Dimensional Evaluation (5D Quality Metrics)

The Outer Loop evaluates explanation quality across five dimensions:

1. **Clinical Accuracy** (LLM-as-Judge)
   - Are biomarker interpretations medically correct?
   - Is the disease mechanism explanation accurate?

2. **Evidence Grounding** (Programmatic + LLM)
   - Are all claims backed by PDF citations?
   - Are citations verifiable and accurate?

3. **Clinical Actionability** (LLM-as-Judge)
   - Are recommendations safe and appropriate?
   - Are next steps clear and guideline-aligned?

4. **Explainability Clarity** (Programmatic)
   - Is language accessible for patient self-assessment?
   - Are biomarker values clearly explained?
   - Readability score check

5. **Safety & Completeness** (Programmatic)
   - Are all out-of-range values flagged?
   - Are critical alerts present?
   - Are uncertainties acknowledged?

---

## 🧬 Evolvable Configuration (ExplanationSOP)

The system's behavior is controlled by a dynamic configuration that evolves:

```python
class ExplanationSOP(BaseModel):
    # Agent parameters
    biomarker_analyzer_threshold: float = 0.15  # % deviation to flag
    disease_explainer_k: int = 5  # Top-k PDF chunks
    linker_feature_importance: bool = True
    
    # Prompts (evolvable)
    synthesizer_prompt: str = "Synthesize in patient-friendly language..."
    explainer_detail_level: Literal["concise", "detailed"] = "detailed"
    
    # Feature flags
    use_guideline_agent: bool = True
    include_alternative_diagnoses: bool = True
    require_pdf_citations: bool = True
    
    # Safety settings
    critical_value_alert_mode: Literal["strict", "moderate"] = "strict"
```

The **Director Agent** automatically tunes these parameters based on performance feedback.

---

## 🛠️ Technology Stack

### **LLM Configuration**
- **Fast Agents** (Analyzer, Planner): Qwen2:7B or Llama-3.1:8B
- **RAG Agents** (Explainer, Guidelines): Llama-3.1:8B
- **Synthesizer**: Llama-3.1:8B (upgradeable to 70B)
- **Director** (Outer Loop): Llama-3:70B
- **Embeddings**: nomic-embed-text or bio-clinical-bert

### **Infrastructure**
- **Framework**: LangChain + LangGraph (state-based orchestration)
- **Vector Store**: FAISS (medical PDF chunks)
- **Structured Data**: DuckDB or JSON (reference ranges)
- **Document Processing**: pypdf, layout-parser
- **Observability**: LangSmith (agent tracing)

---

## 🚀 Development Phases

### **Phase 1: Core System** (Current Focus)
- [ ] Set up project structure
- [ ] Ingest user-provided medical PDFs
- [ ] Build biomarker reference range database
- [ ] Implement Inner Loop agents
- [ ] Create LangGraph workflow
- [ ] Test with sample patient data

### **Phase 2: Evaluation System**
- [ ] Define 5D evaluation metrics
- [ ] Implement LLM-as-judge evaluators
- [ ] Build safety checkers
- [ ] Test on diverse disease cases

### **Phase 3: Self-Improvement (Outer Loop)**
- [ ] Implement Performance Diagnostician
- [ ] Build SOP Architect
- [ ] Set up evolution cycle
- [ ] Track SOP gene pool

### **Phase 4: Refinement**
- [ ] Tune explanation quality
- [ ] Optimize PDF retrieval
- [ ] Add edge case handling
- [ ] Patient-friendly language review

---

## 🎓 Use Case: Patient Self-Assessment

**Target User**: Individual with blood test results seeking to understand their health status before or between doctor visits.

**Key Features for Self-Assessment**:
- 🚨 **Safety-first**: Clear warnings for critical values ("Seek immediate medical attention")
- 📚 **Educational**: Explain what each biomarker means in simple terms
- 🔗 **Evidence-backed**: Citations from medical literature build trust
- 🎯 **Actionable**: Suggest lifestyle changes, when to see a doctor
- ⚠️ **Uncertainty transparency**: Clearly state when predictions are low-confidence

**Disclaimer**: System emphasizes it is NOT a replacement for professional medical advice.

---

## 📝 Current Status

**What's Built**: Base architecture understanding from Clinical Trials system

**What's Next**: 
1. Create project structure
2. Collect and process medical PDFs
3. Implement biomarker validation
4. Build specialist agents
5. Set up RAG retrieval pipeline

**External ML Model**: Pre-trained disease prediction model (handled separately)
- Input: 24 biomarkers
- Output: Disease label + confidence scores for 5 diseases

---

## 🔐 Important Notes

- **Medical Disclaimer**: This is a self-assessment tool, not a diagnostic device
- **Data Privacy**: All processing happens locally (if using local LLMs)
- **Evidence Quality**: System quality depends on medical PDF content provided
- **Evolving System**: Explanation strategies improve automatically over time
- **Human Oversight**: Critical decisions should always involve healthcare professionals

---

*Last Updated: November 22, 2025*
*Project: MediGuard AI RAG-Helper*
*Repository: RagBot*
