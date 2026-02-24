"""
MediGuard AI — Airflow DAG: SOP Evolution Cycle

Runs the evolutionary SOP optimisation loop periodically.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "mediguard",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "email_on_failure": False,
}


def _run_evolution(**kwargs):
    """Execute one SOP evolution cycle."""
    from src.evolution.director import run_evolution_cycle

    result = run_evolution_cycle()
    print(f"Evolution cycle complete: {result}")
    return result


with DAG(
    dag_id="mediguard_sop_evolution",
    default_args=default_args,
    description="Run SOP evolutionary optimisation",
    schedule="@weekly",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mediguard", "evolution"],
) as dag:
    evolve = PythonOperator(
        task_id="run_sop_evolution",
        python_callable=_run_evolution,
    )
