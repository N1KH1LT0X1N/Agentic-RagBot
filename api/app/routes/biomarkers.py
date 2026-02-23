"""
Biomarkers List Endpoint
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.models.schemas import BiomarkersListResponse, BiomarkerInfo, BiomarkerReferenceRange


router = APIRouter(prefix="/api/v1", tags=["biomarkers"])


@router.get("/biomarkers", response_model=BiomarkersListResponse)
async def list_biomarkers():
    """
    Get list of all supported biomarkers with reference ranges.
    
    Returns comprehensive information about all 24 biomarkers:
    - Name and unit
    - Normal reference ranges (gender-specific if applicable)
    - Critical thresholds
    - Clinical significance
    
    Useful for:
    - Frontend validation
    - Understanding what biomarkers can be analyzed
    - Getting reference ranges for display
    """
    
    try:
        # Load biomarker references
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "biomarker_references.json"
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        biomarkers_data = config_data.get("biomarkers", {})
        
        biomarkers_list = []
        
        for name, info in biomarkers_data.items():
            # Parse reference range
            normal_range_data = info.get("normal_range", {})
            
            if "male" in normal_range_data or "female" in normal_range_data:
                # Gender-specific ranges
                reference_range = BiomarkerReferenceRange(
                    min=None,
                    max=None,
                    male=normal_range_data.get("male"),
                    female=normal_range_data.get("female")
                )
            else:
                # Universal range
                reference_range = BiomarkerReferenceRange(
                    min=normal_range_data.get("min"),
                    max=normal_range_data.get("max"),
                    male=None,
                    female=None
                )
            
            biomarker_info = BiomarkerInfo(
                name=name,
                unit=info.get("unit", ""),
                normal_range=reference_range,
                critical_low=info.get("critical_low"),
                critical_high=info.get("critical_high"),
                gender_specific=info.get("gender_specific", False),
                description=info.get("description", ""),
                clinical_significance=info.get("clinical_significance", {})
            )
            
            biomarkers_list.append(biomarker_info)
        
        return BiomarkersListResponse(
            biomarkers=biomarkers_list,
            total_count=len(biomarkers_list),
            timestamp=datetime.now().isoformat()
        )
    
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Biomarker configuration file not found"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load biomarkers: {str(e)}"
        )
