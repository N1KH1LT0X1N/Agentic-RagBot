"""
Evolution Engine Package
Self-improvement system for SOP optimization
"""

from .director import (
    SOPGenePool,
    Diagnosis,
    SOPMutation,
    EvolvedSOPs,
    performance_diagnostician,
    sop_architect,
    run_evolution_cycle
)

from .pareto import (
    identify_pareto_front,
    visualize_pareto_frontier,
    print_pareto_summary,
    analyze_improvements
)

__all__ = [
    'SOPGenePool',
    'Diagnosis',
    'SOPMutation',
    'EvolvedSOPs',
    'performance_diagnostician',
    'sop_architect',
    'run_evolution_cycle',
    'identify_pareto_front',
    'visualize_pareto_frontier',
    'print_pareto_summary',
    'analyze_improvements'
]
