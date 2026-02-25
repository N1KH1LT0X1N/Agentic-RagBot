"""
Evolution Engine Package
Self-improvement system for SOP optimization
"""

from .director import (
    Diagnosis,
    EvolvedSOPs,
    SOPGenePool,
    SOPMutation,
    performance_diagnostician,
    run_evolution_cycle,
    sop_architect,
)
from .pareto import analyze_improvements, identify_pareto_front, print_pareto_summary, visualize_pareto_frontier

__all__ = [
    'Diagnosis',
    'EvolvedSOPs',
    'SOPGenePool',
    'SOPMutation',
    'analyze_improvements',
    'identify_pareto_front',
    'performance_diagnostician',
    'print_pareto_summary',
    'run_evolution_cycle',
    'sop_architect',
    'visualize_pareto_frontier'
]
