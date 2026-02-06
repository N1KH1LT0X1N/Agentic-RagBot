/* ============================================================================
   RagBot API Integration - Ready to Copy & Paste
   ============================================================================
   
   Add this to your website to integrate RagBot medical analysis
   
   Prerequisites:
   1. RagBot API server running on http://localhost:8000 (or your server URL)
   2. CORS is already enabled - no configuration needed!
   
   ============================================================================ */

// Configuration
const RAGBOT_API_URL = 'http://localhost:8000';  // Change to your server URL

// ============================================================================
// 1. SIMPLE EXAMPLE - Get Pre-run Diabetes Analysis
// ============================================================================

async function getExampleAnalysis() {
    try {
        const response = await fetch(`${RAGBOT_API_URL}/api/v1/example`);
        const data = await response.json();
        
        console.log('Predicted Disease:', data.analysis.prediction.predicted_disease);
        console.log('Confidence:', data.analysis.prediction.confidence);
        console.log('Full Response:', data);
        
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// Usage:
// getExampleAnalysis().then(data => displayResults(data));


// ============================================================================
// 2. CUSTOM ANALYSIS - Submit Patient Biomarkers
// ============================================================================

async function analyzePatientBiomarkers(biomarkers, patientContext = {}) {
    try {
        const response = await fetch(`${RAGBOT_API_URL}/api/v1/analyze/structured`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                biomarkers: biomarkers,
                patient_context: patientContext
            })
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error('Error analyzing biomarkers:', error);
        throw error;
    }
}

// Usage Example:
/*
const biomarkers = {
    glucose: 180,        // mg/dL
    hba1c: 8.2,         // %
    ldl: 145,           // mg/dL
    hdl: 35,            // mg/dL
    triglycerides: 220  // mg/dL
};

const patientContext = {
    age: 55,
    gender: 'male',
    bmi: 28.5
};

analyzePatientBiomarkers(biomarkers, patientContext)
    .then(data => {
        console.log('Disease:', data.analysis.prediction.predicted_disease);
        console.log('Confidence:', data.analysis.prediction.confidence);
        console.log('Biomarker Flags:', data.analysis.biomarker_flags);
        console.log('Safety Alerts:', data.analysis.safety_alerts);
        console.log('Recommendations:', data.analysis.recommendations);
    })
    .catch(error => console.error('Failed:', error));
*/


// ============================================================================
// 3. NATURAL LANGUAGE INPUT (Requires Ollama)
// ============================================================================

async function analyzeNaturalLanguage(text, patientContext = {}) {
    try {
        const response = await fetch(`${RAGBOT_API_URL}/api/v1/analyze/natural`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                text: text,
                patient_context: patientContext
            })
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error('Error analyzing text:', error);
        throw error;
    }
}

// Usage Example:
/*
const patientDescription = "The patient's glucose level is 180 and HbA1c is 8.2. LDL cholesterol is 145.";

analyzeNaturalLanguage(patientDescription, { age: 55, gender: 'male' })
    .then(data => console.log('Analysis:', data))
    .catch(error => console.error('Failed:', error));
*/


// ============================================================================
// 4. GET AVAILABLE BIOMARKERS
// ============================================================================

async function getAvailableBiomarkers() {
    try {
        const response = await fetch(`${RAGBOT_API_URL}/api/v1/biomarkers`);
        const data = await response.json();
        
        console.log('Total Biomarkers:', data.total);
        console.log('Biomarkers:', data.biomarkers);
        
        return data.biomarkers;
        
    } catch (error) {
        console.error('Error fetching biomarkers:', error);
        throw error;
    }
}

// Usage:
// getAvailableBiomarkers().then(biomarkers => populateDropdown(biomarkers));


// ============================================================================
// 5. HEALTH CHECK
// ============================================================================

async function checkAPIHealth() {
    try {
        const response = await fetch(`${RAGBOT_API_URL}/api/v1/health`);
        const data = await response.json();
        
        return {
            isOnline: data.status === 'healthy',
            ragbotReady: data.ragbot_initialized,
            details: data
        };
        
    } catch (error) {
        console.error('API is offline:', error);
        return {
            isOnline: false,
            ragbotReady: false,
            error: error.message
        };
    }
}

// Usage:
// checkAPIHealth().then(health => {
//     if (health.isOnline) {
//         console.log('API is ready!');
//     } else {
//         console.log('API is offline');
//     }
// });


// ============================================================================
// 6. COMPLETE EXAMPLE - HTML Form Integration
// ============================================================================

/*
<!-- HTML Form Example -->
<form id="biomarkerForm">
    <h3>Patient Biomarkers</h3>
    
    <label>Glucose (mg/dL):</label>
    <input type="number" id="glucose" name="glucose" placeholder="70-100">
    
    <label>HbA1c (%):</label>
    <input type="number" id="hba1c" name="hba1c" step="0.1" placeholder="4-6">
    
    <label>LDL (mg/dL):</label>
    <input type="number" id="ldl" name="ldl" placeholder="< 100">
    
    <label>HDL (mg/dL):</label>
    <input type="number" id="hdl" name="hdl" placeholder="> 40">
    
    <h3>Patient Context</h3>
    
    <label>Age:</label>
    <input type="number" id="age" name="age" placeholder="18-100">
    
    <label>Gender:</label>
    <select id="gender" name="gender">
        <option value="male">Male</option>
        <option value="female">Female</option>
    </select>
    
    <button type="submit">Analyze</button>
</form>

<div id="results"></div>

<script>
document.getElementById('biomarkerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Collect biomarkers
    const biomarkers = {};
    const fields = ['glucose', 'hba1c', 'ldl', 'hdl'];
    fields.forEach(field => {
        const value = parseFloat(document.getElementById(field).value);
        if (value) biomarkers[field] = value;
    });
    
    // Collect patient context
    const patientContext = {
        age: parseInt(document.getElementById('age').value) || undefined,
        gender: document.getElementById('gender').value
    };
    
    // Show loading
    document.getElementById('results').innerHTML = '<p>Analyzing...</p>';
    
    try {
        // Call API
        const data = await analyzePatientBiomarkers(biomarkers, patientContext);
        
        // Display results
        displayResults(data);
        
    } catch (error) {
        document.getElementById('results').innerHTML = 
            `<p style="color: red;">Error: ${error.message}</p>`;
    }
});

function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    
    const html = `
        <h3>Analysis Results</h3>
        <p><strong>Predicted Disease:</strong> ${data.analysis.prediction.predicted_disease}</p>
        <p><strong>Confidence:</strong> ${(data.analysis.prediction.confidence * 100).toFixed(1)}%</p>
        
        <h4>Biomarker Flags (${data.analysis.biomarker_flags.length})</h4>
        <ul>
            ${data.analysis.biomarker_flags.map(flag => 
                `<li><strong>${flag.biomarker}</strong>: ${flag.value} ${flag.unit} 
                 (${flag.status}) - ${flag.interpretation}</li>`
            ).join('')}
        </ul>
        
        ${data.analysis.safety_alerts.length > 0 ? `
            <h4 style="color: red;">⚠️ Safety Alerts</h4>
            <ul>
                ${data.analysis.safety_alerts.map(alert => 
                    `<li><strong>${alert.severity}</strong>: ${alert.message}</li>`
                ).join('')}
            </ul>
        ` : ''}
        
        <h4>Key Drivers</h4>
        <ul>
            ${data.analysis.key_drivers.map(driver => 
                `<li>${driver.biomarker}: ${driver.impact}</li>`
            ).join('')}
        </ul>
        
        <h4>Recommendations</h4>
        ${data.analysis.recommendations.immediate_actions.length > 0 ? `
            <p><strong>Immediate Actions:</strong></p>
            <ul>
                ${data.analysis.recommendations.immediate_actions.map(action => 
                    `<li>${action}</li>`
                ).join('')}
            </ul>
        ` : ''}
        
        <details>
            <summary>View Full Response</summary>
            <pre>${JSON.stringify(data, null, 2)}</pre>
        </details>
    `;
    
    resultsDiv.innerHTML = html;
}
</script>
*/


// ============================================================================
// 7. REACT INTEGRATION EXAMPLE
// ============================================================================

/*
import React, { useState } from 'react';

const RAGBOT_API_URL = 'http://localhost:8000';

function BiomarkerAnalysis() {
    const [biomarkers, setBiomarkers] = useState({
        glucose: '',
        hba1c: '',
        ldl: '',
        hdl: ''
    });
    
    const [patientContext, setPatientContext] = useState({
        age: '',
        gender: 'male'
    });
    
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    const handleAnalyze = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        
        try {
            // Filter out empty values
            const cleanBiomarkers = Object.entries(biomarkers)
                .filter(([_, value]) => value !== '')
                .reduce((acc, [key, value]) => ({
                    ...acc,
                    [key]: parseFloat(value)
                }), {});
            
            const cleanContext = {
                age: patientContext.age ? parseInt(patientContext.age) : undefined,
                gender: patientContext.gender
            };
            
            const response = await fetch(`${RAGBOT_API_URL}/api/v1/analyze/structured`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    biomarkers: cleanBiomarkers,
                    patient_context: cleanContext
                })
            });
            
            if (!response.ok) throw new Error('Analysis failed');
            
            const data = await response.json();
            setResults(data);
            
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div>
            <h2>Biomarker Analysis</h2>
            
            <form onSubmit={handleAnalyze}>
                <input
                    type="number"
                    placeholder="Glucose (mg/dL)"
                    value={biomarkers.glucose}
                    onChange={(e) => setBiomarkers({...biomarkers, glucose: e.target.value})}
                />
                
                <input
                    type="number"
                    placeholder="HbA1c (%)"
                    value={biomarkers.hba1c}
                    onChange={(e) => setBiomarkers({...biomarkers, hba1c: e.target.value})}
                />
                
                <button type="submit" disabled={loading}>
                    {loading ? 'Analyzing...' : 'Analyze'}
                </button>
            </form>
            
            {error && <div style={{color: 'red'}}>{error}</div>}
            
            {results && (
                <div>
                    <h3>Results</h3>
                    <p>Disease: {results.analysis.prediction.predicted_disease}</p>
                    <p>Confidence: {(results.analysis.prediction.confidence * 100).toFixed(1)}%</p>
                    {/* Display more results... *\/}
                </div>
            )}
        </div>
    );
}

export default BiomarkerAnalysis;
*/


// ============================================================================
// 8. ERROR HANDLING HELPER
// ============================================================================

function handleAPIError(error) {
    if (error.message.includes('Failed to fetch')) {
        return {
            type: 'connection',
            message: 'Cannot connect to API server. Make sure it is running on ' + RAGBOT_API_URL,
            suggestion: 'Run: .\\run_api.ps1'
        };
    } else if (error.message.includes('API Error: 422')) {
        return {
            type: 'validation',
            message: 'Invalid input data. Please check your biomarker values.',
            suggestion: 'Ensure all numeric values are valid numbers'
        };
    } else if (error.message.includes('API Error: 500')) {
        return {
            type: 'server',
            message: 'Server error occurred during analysis.',
            suggestion: 'Check the API server logs for details'
        };
    } else {
        return {
            type: 'unknown',
            message: error.message,
            suggestion: 'Check browser console for details'
        };
    }
}

// Usage:
/*
try {
    const data = await analyzePatientBiomarkers(biomarkers, context);
} catch (error) {
    const errorInfo = handleAPIError(error);
    alert(`${errorInfo.message}\n\nSuggestion: ${errorInfo.suggestion}`);
}
*/


// ============================================================================
// EXPORT (if using modules)
// ============================================================================

// export {
//     getExampleAnalysis,
//     analyzePatientBiomarkers,
//     analyzeNaturalLanguage,
//     getAvailableBiomarkers,
//     checkAPIHealth,
//     handleAPIError
// };
