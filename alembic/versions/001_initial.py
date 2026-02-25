"""initial_tables

Revision ID: 001
Revises: 
Create Date: 2026-02-24 20:58:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'patient_analyses',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=64), nullable=False),
        sa.Column('biomarkers', sa.JSON(), nullable=False),
        sa.Column('patient_context', sa.JSON(), nullable=True),
        sa.Column('predicted_disease', sa.String(length=128), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('probabilities', sa.JSON(), nullable=True),
        sa.Column('analysis_result', sa.JSON(), nullable=True),
        sa.Column('safety_alerts', sa.JSON(), nullable=True),
        sa.Column('sop_version', sa.String(length=64), nullable=True),
        sa.Column('processing_time_ms', sa.Float(), nullable=False),
        sa.Column('model_provider', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patient_analyses_request_id'), 'patient_analyses', ['request_id'], unique=True)

    op.create_table(
        'medical_documents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('source', sa.String(length=512), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('authors', sa.Text(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=True),
        sa.Column('parse_status', sa.String(length=32), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_hash')
    )
    op.create_index(op.f('ix_medical_documents_title'), 'medical_documents', ['title'], unique=False)

    op.create_table(
        'sop_versions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('version_tag', sa.String(length=64), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('evaluation_scores', sa.JSON(), nullable=True),
        sa.Column('parent_version', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sop_versions_version_tag'), 'sop_versions', ['version_tag'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_sop_versions_version_tag'), table_name='sop_versions')
    op.drop_table('sop_versions')

    op.drop_index(op.f('ix_medical_documents_title'), table_name='medical_documents')
    op.drop_table('medical_documents')

    op.drop_index(op.f('ix_patient_analyses_request_id'), table_name='patient_analyses')
    op.drop_table('patient_analyses')
