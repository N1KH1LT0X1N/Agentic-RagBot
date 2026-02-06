"""
Pareto Frontier Analysis
Identifies optimal trade-offs in multi-objective optimization
"""

import numpy as np
from typing import List, Dict, Any
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def identify_pareto_front(gene_pool_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identifies non-dominated solutions (Pareto Frontier).
    
    A solution is dominated if another solution is:
    - Better or equal on ALL metrics
    - Strictly better on AT LEAST ONE metric
    """
    pareto_front = []
    
    for i, candidate in enumerate(gene_pool_entries):
        is_dominated = False
        
        # Get candidate's 5D score vector
        cand_scores = np.array(candidate['evaluation'].to_vector())
        
        for j, other in enumerate(gene_pool_entries):
            if i == j:
                continue
            
            # Get other solution's 5D vector
            other_scores = np.array(other['evaluation'].to_vector())
            
            # Check domination: other >= candidate on ALL, other > candidate on SOME
            if np.all(other_scores >= cand_scores) and np.any(other_scores > cand_scores):
                is_dominated = True
                break
        
        if not is_dominated:
            pareto_front.append(candidate)
    
    return pareto_front


def visualize_pareto_frontier(pareto_front: List[Dict[str, Any]]):
    """
    Creates two visualizations:
    1. Parallel coordinates plot (5D)
    2. Radar chart (5D profile)
    """
    if not pareto_front:
        print("No solutions on Pareto front to visualize")
        return
    
    fig = plt.figure(figsize=(18, 7))
    
    # --- Plot 1: Bar Chart (since pandas might not be available) ---
    ax1 = plt.subplot(1, 2, 1)
    
    metrics = ['Clinical\nAccuracy', 'Evidence\nGrounding', 'Actionability', 'Clarity', 'Safety']
    x = np.arange(len(metrics))
    width = 0.8 / len(pareto_front)
    
    for idx, entry in enumerate(pareto_front):
        e = entry['evaluation']
        scores = [
            e.clinical_accuracy.score,
            e.evidence_grounding.score,
            e.actionability.score,
            e.clarity.score,
            e.safety_completeness.score
        ]
        
        offset = (idx - len(pareto_front) / 2) * width + width / 2
        label = f"SOP v{entry['version']}"
        ax1.bar(x + offset, scores, width, label=label, alpha=0.8)
    
    ax1.set_xlabel('Metrics', fontsize=12)
    ax1.set_ylabel('Score', fontsize=12)
    ax1.set_title('5D Performance Comparison (Bar Chart)', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=10)
    ax1.set_ylim(0, 1.0)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # --- Plot 2: Radar Chart ---
    ax2 = plt.subplot(1, 2, 2, projection='polar')
    
    categories = ['Clinical\nAccuracy', 'Evidence\nGrounding', 
                  'Actionability', 'Clarity', 'Safety']
    num_vars = len(categories)
    
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]
    
    for entry in pareto_front:
        e = entry['evaluation']
        values = [
            e.clinical_accuracy.score,
            e.evidence_grounding.score,
            e.actionability.score,
            e.clarity.score,
            e.safety_completeness.score
        ]
        values += values[:1]
        
        desc = entry.get('description', '')[:30]
        label = f"SOP v{entry['version']}: {desc}"
        ax2.plot(angles, values, 'o-', linewidth=2, label=label)
        ax2.fill(angles, values, alpha=0.15)
    
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(categories, size=10)
    ax2.set_ylim(0, 1)
    ax2.set_title('5D Performance Profiles (Radar Chart)', size=14, y=1.08)
    ax2.legend(loc='upper left', bbox_to_anchor=(1.2, 1.0), fontsize=9)
    ax2.grid(True)
    
    plt.tight_layout()
    
    # Create data directory if it doesn't exist
    from pathlib import Path
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    output_path = data_dir / 'pareto_frontier_analysis.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Visualization saved to: {output_path}")


def print_pareto_summary(pareto_front: List[Dict[str, Any]]):
    """Print human-readable summary of Pareto frontier"""
    print("\n" + "=" * 80)
    print("PARETO FRONTIER ANALYSIS")
    print("=" * 80)
    
    print(f"\nFound {len(pareto_front)} optimal (non-dominated) solutions:\n")
    
    for entry in pareto_front:
        v = entry['version']
        p = entry.get('parent')
        desc = entry.get('description', 'Baseline')
        e = entry['evaluation']
        
        print(f"SOP v{v} {f'(Child of v{p})' if p else '(Baseline)'}")
        print(f"  Description: {desc}")
        print(f"  Clinical Accuracy:     {e.clinical_accuracy.score:.3f}")
        print(f"  Evidence Grounding:    {e.evidence_grounding.score:.3f}")
        print(f"  Actionability:         {e.actionability.score:.3f}")
        print(f"  Clarity:               {e.clarity.score:.3f}")
        print(f"  Safety & Completeness: {e.safety_completeness.score:.3f}")
        
        # Calculate average
        avg_score = np.mean(e.to_vector())
        print(f"  Average Score:         {avg_score:.3f}")
        print()
    
    print("=" * 80)
    print("\nRECOMMENDATION:")
    print("Review the visualizations and choose the SOP that best matches")
    print("your strategic priorities (e.g., maximum accuracy vs. clarity).")
    print("=" * 80)


def analyze_improvements(gene_pool_entries: List[Dict[str, Any]]):
    """Analyze improvements over baseline"""
    if len(gene_pool_entries) < 2:
        print("\n⚠️ Not enough SOPs to analyze improvements")
        return
    
    baseline = gene_pool_entries[0]
    baseline_scores = np.array(baseline['evaluation'].to_vector())
    
    print("\n" + "=" * 80)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 80)
    
    print(f"\nBaseline (v{baseline['version']}): {baseline.get('description', 'Initial')}")
    print(f"  Average Score: {np.mean(baseline_scores):.3f}")
    
    improvements_found = False
    for entry in gene_pool_entries[1:]:
        scores = np.array(entry['evaluation'].to_vector())
        avg_score = np.mean(scores)
        baseline_avg = np.mean(baseline_scores)
        
        if avg_score > baseline_avg:
            improvements_found = True
            improvement_pct = ((avg_score - baseline_avg) / baseline_avg) * 100
            
            print(f"\n✓ SOP v{entry['version']}: {entry.get('description', '')}") 
            print(f"  Average Score: {avg_score:.3f} (+{improvement_pct:.1f}% vs baseline)")
            
            # Show per-metric improvements
            metric_names = ['Clinical Accuracy', 'Evidence Grounding', 'Actionability', 
                          'Clarity', 'Safety & Completeness']
            for i, (name, score, baseline_score) in enumerate(zip(metric_names, scores, baseline_scores)):
                diff = score - baseline_score
                if abs(diff) > 0.01:  # Show significant changes
                    symbol = "↑" if diff > 0 else "↓"
                    print(f"    {name}: {score:.3f} {symbol} ({diff:+.3f})")
    
    if not improvements_found:
        print("\n⚠️ No improvements found over baseline yet")
        print("   Consider running more evolution cycles or adjusting mutation strategies")
    
    print("\n" + "=" * 80)
