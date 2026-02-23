"""
MediGuard AI — Airflow DAG: Ingest Medical PDFs

Periodically scans the medical_pdfs directory, parses new PDFs,
chunks them, generates embeddings, and indexes into OpenSearch.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "mediguard",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def _ingest_pdfs(**kwargs):
    """Parse all PDFs and index into OpenSearch."""
    from pathlib import Path

    from src.services.embeddings.service import make_embedding_service
    from src.services.indexing.service import IndexingService
    from src.services.opensearch.client import make_opensearch_client
    from src.services.pdf_parser.service import make_pdf_parser_service
    from src.settings import get_settings

    settings = get_settings()
    pdf_dir = Path(settings.medical_pdfs.directory)

    parser = make_pdf_parser_service()
    embedding_svc = make_embedding_service()
    os_client = make_opensearch_client()
    indexing_svc = IndexingService(embedding_svc, os_client)

    docs = parser.parse_directory(pdf_dir)
    indexed = 0
    for doc in docs:
        if doc.full_text and not doc.error:
            indexing_svc.index_text(doc.full_text, {"title": doc.filename})
            indexed += 1

    print(f"Ingested {indexed}/{len(docs)} documents")
    return {"total": len(docs), "indexed": indexed}


with DAG(
    dag_id="mediguard_ingest_pdfs",
    default_args=default_args,
    description="Parse and index medical PDFs into OpenSearch",
    schedule="@daily",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mediguard", "indexing"],
) as dag:
    ingest = PythonOperator(
        task_id="ingest_medical_pdfs",
        python_callable=_ingest_pdfs,
    )
