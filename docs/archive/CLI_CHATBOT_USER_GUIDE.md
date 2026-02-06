# CLI Chatbot User Guide
## Interactive Chat Interface for MediGuard AI RAG-Helper

**Date:** November 23, 2025  
**Status:** ✅ FULLY IMPLEMENTED AND OPERATIONAL

---

## 🎯 Quick Start

### Run the Chatbot
```powershell
python scripts/chat.py
```

### First Time Setup
Make sure you have:
1. ✅ Ollama running: `ollama serve`
2. ✅ Models pulled:
   ```powershell
   ollama pull llama3.1:8b-instruct
   ollama pull qwen2:7b
   ```
3. ✅ Vector store created: `python src/pdf_processor.py` (if not already done)

---

## 💬 How to Use

### Example Conversations

#### **Example 1: Basic Biomarker Input**
```
You: My glucose is 185 and HbA1c is 8.2

🔍 Analyzing your input...
✅ Found 2 biomarkers: Glucose, HbA1c
🧠 Predicting likely condition...
✅ Predicted: Diabetes (85% confidence)
📚 Consulting medical knowledge base...
   (This may take 15-25 seconds...)

🤖 RAG-BOT:
======================================================================
Hi there! 👋
Based on your biomarkers, I analyzed your results.

🔴 **Primary Finding:** Diabetes
   Confidence: 85%

⚠️ **IMPORTANT SAFETY ALERTS:**
   • Glucose: CRITICAL: Glucose is 185.0 mg/dL, above critical threshold
     → SEEK IMMEDIATE MEDICAL ATTENTION

[... full analysis ...]
```

#### **Example 2: Multiple Biomarkers**
```
You: hemoglobin 10.5, RBC 3.8, MCV 78, platelets 180000

✅ Found 4 biomarkers: Hemoglobin, RBC, MCV, Platelets
🧠 Predicting likely condition...
✅ Predicted: Anemia (72% confidence)
```

#### **Example 3: With Patient Context**
```
You: I'm a 52 year old male, glucose 185, cholesterol 235, HDL 38

✅ Found 3 biomarkers: Glucose, Cholesterol, HDL
✅ Patient context: age=52, gender=male
```

---

## 📋 Available Commands

### `help` - Show Biomarker List
Displays all 24 supported biomarkers organized by category.

```
You: help

📋 Supported Biomarkers (24 total):

🩸 Blood Cells:
  • Hemoglobin, Platelets, WBC, RBC, Hematocrit, MCV, MCH, MCHC

🔬 Metabolic:
  • Glucose, Cholesterol, Triglycerides, HbA1c, LDL, HDL, Insulin, BMI

❤️ Cardiovascular:
  • Heart Rate, Systolic BP, Diastolic BP, Troponin, C-reactive Protein

🏥 Organ Function:
  • ALT, AST, Creatinine
```

### `example` - Run Demo Case
Runs a complete example of a Type 2 Diabetes patient with 11 biomarkers.

```
You: example

📋 Running Example: Type 2 Diabetes Patient
   52-year-old male with elevated glucose and HbA1c

🔄 Running analysis...
[... full RAG workflow execution ...]
```

### `quit` - Exit Chatbot
Exits the interactive session gracefully.

```
You: quit

👋 Thank you for using MediGuard AI. Stay healthy!
```

---

## 🩺 Supported Biomarkers (24 Total)

### Blood Cells (8)
| Biomarker | Aliases | Example Input |
|-----------|---------|---------------|
| **Hemoglobin** | HGB, HB | "hemoglobin 13.5" |
| **Platelets** | PLT | "platelets 220000" |
| **WBC** | White Blood Cells | "WBC 7500" |
| **RBC** | Red Blood Cells | "RBC 4.8" |
| **Hematocrit** | HCT | "hematocrit 42" |
| **MCV** | Mean Corpuscular Volume | "MCV 85" |
| **MCH** | Mean Corpuscular Hemoglobin | "MCH 29" |
| **MCHC** | - | "MCHC 34" |

### Metabolic (8)
| Biomarker | Aliases | Example Input |
|-----------|---------|---------------|
| **Glucose** | Blood Sugar | "glucose 140" |
| **Cholesterol** | Total Cholesterol | "cholesterol 220" |
| **Triglycerides** | Trig | "triglycerides 180" |
| **HbA1c** | A1C, Hemoglobin A1c | "HbA1c 7.5" |
| **LDL** | LDL Cholesterol | "LDL 160" |
| **HDL** | HDL Cholesterol | "HDL 45" |
| **Insulin** | - | "insulin 18" |
| **BMI** | Body Mass Index | "BMI 28.5" |

### Cardiovascular (5)
| Biomarker | Aliases | Example Input |
|-----------|---------|---------------|
| **Heart Rate** | HR, Pulse | "heart rate 85" |
| **Systolic BP** | Systolic, SBP | "systolic 145" |
| **Diastolic BP** | Diastolic, DBP | "diastolic 92" |
| **Troponin** | - | "troponin 0.05" |
| **C-reactive Protein** | CRP | "CRP 8.5" |

### Organ Function (3)
| Biomarker | Aliases | Example Input |
|-----------|---------|---------------|
| **ALT** | Alanine Aminotransferase | "ALT 45" |
| **AST** | Aspartate Aminotransferase | "AST 38" |
| **Creatinine** | - | "creatinine 1.1" |

---

## 🎨 Input Formats Supported

The chatbot accepts natural language input in various formats:

### Format 1: Conversational
```
My glucose is 140 and my HbA1c is 7.5
```

### Format 2: List Style
```
Hemoglobin 11.2, platelets 180000, cholesterol 235
```

### Format 3: Structured
```
glucose=185, HbA1c=8.2, HDL=38, triglycerides=210
```

### Format 4: With Context
```
I'm 52 years old male, glucose 185, cholesterol 235
```

### Format 5: Mixed
```
Blood test results: glucose is 140, my HbA1c came back at 7.5%, and cholesterol is 220
```

---

## 🔍 How It Works

### 1. Biomarker Extraction (LLM)
- Uses `llama3.1:8b-instruct` to extract biomarkers from natural language
- Normalizes biomarker names (e.g., "A1C" → "HbA1c")
- Extracts patient context (age, gender, BMI)

### 2. Disease Prediction (LLM)
- Uses `qwen2:7b` to predict disease based on biomarker patterns
- Returns: disease name, confidence score, probability distribution
- Fallback: Rule-based prediction if LLM fails

### 3. RAG Workflow Execution
- Runs complete 6-agent workflow:
  1. Biomarker Analyzer
  2. Disease Explainer (RAG)
  3. Biomarker-Disease Linker (RAG)
  4. Clinical Guidelines (RAG)
  5. Confidence Assessor
  6. Response Synthesizer

### 4. Conversational Formatting
- Converts technical JSON → friendly text
- Emoji indicators
- Safety alerts highlighted
- Clear structure with sections

---

## 💾 Saving Reports

After each analysis, you'll be asked:

```
💾 Save detailed report to file? (y/n):
```

If you choose **`y`**:
- Report saved to: `data/chat_reports/report_Diabetes_YYYYMMDD_HHMMSS.json`
- Contains: Input biomarkers + Complete analysis JSON
- Can be reviewed later or shared with healthcare providers

---

## ⚠️ Important Notes

### Minimum Requirements
- **At least 2 biomarkers** needed for analysis
- More biomarkers = more accurate predictions

### System Requirements
- **RAM:** 2GB minimum (2.5-3GB recommended)
- **Ollama:** Must be running (`ollama serve`)
- **Models:** llama3.1:8b-instruct, qwen2:7b

### Limitations
1. **Not a Medical Device** - For educational/informational purposes only
2. **No Real ML Model** - Uses LLM-based prediction (not trained ML model)
3. **Standard Units Only** - Enter values in standard medical units
4. **Manual Entry** - Must type biomarkers (no PDF upload yet)

---

## 🐛 Troubleshooting

### Issue 1: "Failed to initialize system"
**Cause:** Ollama not running or models not available

**Solution:**
```powershell
# Start Ollama
ollama serve

# Pull required models
ollama pull llama3.1:8b-instruct
ollama pull qwen2:7b
```

### Issue 2: "I couldn't find any biomarker values"
**Cause:** LLM couldn't extract biomarkers from input

**Solution:**
- Use clearer format: "glucose 140, HbA1c 7.5"
- Type `help` to see biomarker names
- Check spelling

### Issue 3: "Analysis failed: Ollama call failed"
**Cause:** Insufficient system memory or Ollama timeout

**Solution:**
- Close other applications
- Restart Ollama
- Try again with fewer biomarkers

### Issue 4: Unicode/Emoji Display Issues
**Solution:** Already handled! Script automatically sets UTF-8 encoding.

---

## 📊 Example Output Structure

```
Hi there! 👋
Based on your biomarkers, I analyzed your results.

🔴 **Primary Finding:** Diabetes
   Confidence: 87%

⚠️ **IMPORTANT SAFETY ALERTS:**
   • Glucose: CRITICAL: Glucose is 185.0 mg/dL
     → SEEK IMMEDIATE MEDICAL ATTENTION

🔍 **Why this prediction?**
   • **Glucose** (185.0 mg/dL): Significantly elevated...
   • **HbA1c** (8.2%): Poor glycemic control...

✅ **What You Should Do:**
   1. Consult healthcare provider immediately
   2. Bring lab results to appointment

🌱 **Lifestyle Recommendations:**
   1. Follow balanced diet
   2. Regular physical activity
   3. Monitor blood sugar

ℹ️ **Important:** This is AI-assisted analysis, NOT medical advice.
   Please consult a healthcare professional.
```

---

## 🚀 Performance

| Metric | Typical Value |
|--------|---------------|
| **Biomarker Extraction** | 3-5 seconds |
| **Disease Prediction** | 2-3 seconds |
| **RAG Workflow** | 15-25 seconds |
| **Total Time** | ~20-30 seconds |

---

## 🔮 Future Features (Planned)

### Phase 2 Enhancements
- [ ] **Multi-turn conversations** - Answer follow-up questions
- [ ] **PDF lab report upload** - Extract from scanned reports
- [ ] **Unit conversion** - Support mg/dL ↔ mmol/L
- [ ] **Trend tracking** - Compare with previous results
- [ ] **Voice input** - Speak biomarkers instead of typing

### Phase 3 Enhancements
- [ ] **Web interface** - Browser-based chat
- [ ] **Real ML model integration** - Professional disease prediction
- [ ] **Multi-language support** - Spanish, Chinese, etc.

---

## 📚 Technical Details

### Architecture
```
User Input (Natural Language)
    ↓
extract_biomarkers() [llama3.1:8b]
    ↓
predict_disease_llm() [qwen2:7b]
    ↓
create_guild().run() [6 agents, RAG, LangGraph]
    ↓
format_conversational()
    ↓
Conversational Output
```

### Files
- **Main Script:** `scripts/chat.py` (~620 lines)
- **Config:** `config/biomarker_references.json`
- **Reports:** `data/chat_reports/*.json`

### Dependencies
- `langchain_community` - LLM interfaces
- `langchain_core` - Prompts
- Existing `src/` modules - Core RAG system

---

## ✅ Validation

### Tested Scenarios
✅ Diabetes patient (glucose, HbA1c elevated)  
✅ Anemia patient (low hemoglobin, MCV)  
✅ Heart disease indicators (cholesterol, troponin)  
✅ Minimal input (2 biomarkers)  
✅ Invalid input handling  
✅ Help command  
✅ Example command  
✅ Report saving  
✅ Graceful exit  

---

## 🎓 Best Practices

### For Accurate Results
1. **Provide at least 3-5 biomarkers** for reliable analysis
2. **Include key indicators** for the condition you suspect
3. **Mention patient context** (age, gender) when relevant
4. **Use standard medical units** (mg/dL for glucose, % for HbA1c)

### Safety
1. **Always consult a doctor** - This is NOT medical advice
2. **Don't delay emergency care** - Critical alerts require immediate attention
3. **Share reports with healthcare providers** - Save and bring JSON reports

---

## 📞 Support

### Questions?
- Review documentation: `docs/CLI_CHATBOT_IMPLEMENTATION_PLAN.md`
- Check system verification: `docs/SYSTEM_VERIFICATION.md`
- See project overview: `README.md`

### Issues?
- Check Ollama is running: `ollama list`
- Verify models are available
- Review error messages carefully

---

## 📝 Example Session

```
PS> python scripts/chat.py

======================================================================
🤖 MediGuard AI RAG-Helper - Interactive Chat
======================================================================

Welcome! I can help you understand your blood test results.

You can:
  1. Describe your biomarkers (e.g., 'My glucose is 140, HbA1c is 7.5')
  2. Type 'example' to see a sample diabetes case
  3. Type 'help' for biomarker list
  4. Type 'quit' to exit

======================================================================

🔧 Initializing medical knowledge system...
✅ System ready!

You: my glucose is 185 and HbA1c is 8.2

🔍 Analyzing your input...
✅ Found 2 biomarkers: Glucose, HbA1c
🧠 Predicting likely condition...
✅ Predicted: Diabetes (85% confidence)
📚 Consulting medical knowledge base...
   (This may take 15-25 seconds...)

🤖 RAG-BOT:
======================================================================
[... full conversational response ...]
======================================================================

💾 Save detailed report to file? (y/n): y
✅ Report saved to: data/chat_reports/report_Diabetes_20251123_071530.json

You can:
  • Enter more biomarkers for a new analysis
  • Type 'quit' to exit

You: quit

👋 Thank you for using MediGuard AI. Stay healthy!
```

---

**Status:** ✅ FULLY OPERATIONAL  
**Version:** 1.0  
**Last Updated:** November 23, 2025

*MediGuard AI RAG-Helper - Making medical insights accessible through conversation* 🏥💬
