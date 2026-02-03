"""
Alembic Migration: Add Document Classification and Missing Data Pipeline

Creates tables for:
- document_ocr: Stores OCR text and extraction metadata
- missing_data_tasks: Tracks required parameters not extracted
- health_index_snapshots: Stores computed health scores over time

Updates:
- reports table: Add classification columns (category, doc_type, etc.)
- observations table: Add source, user_corrected columns
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4b7c2e891234'
down_revision = '3a8f12d90123'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Needed for `gen_random_uuid()` server defaults in Postgres.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())

    def _has_table(name: str) -> bool:
        return name in existing_tables

    def _has_column(table: str, column: str) -> bool:
        try:
            return column in {c["name"] for c in insp.get_columns(table)}
        except Exception:
            return False

    def _has_index(table: str, index_name: str) -> bool:
        try:
            return index_name in {i["name"] for i in insp.get_indexes(table)}
        except Exception:
            return False

    # ===========================================================================
    # 1. Create document_ocr table
    # ===========================================================================
    if not _has_table('document_ocr'):
        op.create_table(
            'document_ocr',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('ocr_text', sa.Text, nullable=True),
            sa.Column('ocr_json', postgresql.JSONB, nullable=True),  # page_stats, method, confidence
            sa.Column('extraction_method', sa.String(20), nullable=True),  # text/ocr/hybrid
            sa.Column('total_chars', sa.Integer, nullable=True),
            sa.Column('total_pages', sa.Integer, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
        )
        op.create_index('ix_document_ocr_document_id', 'document_ocr', ['document_id'])

    # ===========================================================================
    # 2. Create missing_data_tasks table
    # ===========================================================================
    if not _has_table('missing_data_tasks'):
        op.create_table(
            'missing_data_tasks',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
            sa.Column('metric_key', sa.String(100), nullable=False),
            sa.Column('label', sa.String(200), nullable=False),  # Human-readable label
            sa.Column('expected_unit', sa.String(50), nullable=True),
            sa.Column('required', sa.Boolean, default=False, nullable=False),
            sa.Column('status', sa.String(20), default='pending', nullable=False),  # pending/resolved/skipped
            sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
            sa.Column('resolved_at', sa.DateTime, nullable=True),
        )
        op.create_index('ix_missing_data_tasks_user_document', 'missing_data_tasks', ['user_id', 'document_id'])
        op.create_index('ix_missing_data_tasks_status', 'missing_data_tasks', ['user_id', 'status'])

    # ===========================================================================
    # 3. Create health_index_snapshots table
    # ===========================================================================
    if not _has_table('health_index_snapshots'):
        op.create_table(
            'health_index_snapshots',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('score', sa.Float, nullable=False),
            sa.Column('confidence', sa.Float, nullable=True),
            sa.Column('contributions', postgresql.JSONB, nullable=True),  # Factor breakdown
            sa.Column('missing_inputs', postgresql.JSONB, nullable=True),  # What data was missing
            sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
        )
        op.create_index('ix_health_index_snapshots_user_created', 'health_index_snapshots', ['user_id', 'created_at'])

    # ===========================================================================
    # 4. Add classification columns to reports table
    # ===========================================================================
    if _has_table('reports') and not _has_column('reports', 'category'):
        op.add_column('reports', sa.Column('category', sa.String(50), nullable=True))
    if _has_table('reports') and not _has_column('reports', 'doc_type'):
        op.add_column('reports', sa.Column('doc_type', sa.String(50), nullable=True))
    if _has_table('reports') and not _has_column('reports', 'classification_confidence'):
        op.add_column('reports', sa.Column('classification_confidence', sa.Float, nullable=True))
    if _has_table('reports') and not _has_column('reports', 'classification_rules_matched'):
        op.add_column('reports', sa.Column('classification_rules_matched', postgresql.JSONB, nullable=True))
    if _has_table('reports') and not _has_column('reports', 'extraction_source'):
        op.add_column('reports', sa.Column('extraction_source', sa.String(20), nullable=True))  # regex/grok/manual
    
    if _has_table('reports'):
        if not _has_index('reports', 'ix_reports_category'):
            op.create_index('ix_reports_category', 'reports', ['category'])
        if not _has_index('reports', 'ix_reports_doc_type'):
            op.create_index('ix_reports_doc_type', 'reports', ['doc_type'])
        if not _has_index('reports', 'ix_reports_user_uploaded'):
            op.create_index('ix_reports_user_uploaded', 'reports', ['user_id', 'uploaded_at'])

    # ===========================================================================
    # 5. Add source and user_corrected columns to observations table
    # ===========================================================================
    if _has_table('observations') and not _has_column('observations', 'source'):
        op.add_column('observations', sa.Column('source', sa.String(20), nullable=True))  # regex/grok/manual
    if _has_table('observations') and not _has_column('observations', 'confidence'):
        op.add_column('observations', sa.Column('confidence', sa.Float, nullable=True))
    if _has_table('observations') and not _has_column('observations', 'user_corrected'):
        op.add_column('observations', sa.Column('user_corrected', sa.Boolean, default=False, nullable=False, server_default='false'))
    
    # Index for fetching latest metrics per user
    if _has_table('observations'):
        if not _has_index('observations', 'ix_observations_user_metric_observed'):
            op.create_index('ix_observations_user_metric_observed', 'observations', ['user_id', 'metric_name', 'observed_at'])
        if not _has_index('observations', 'ix_observations_user_abnormal'):
            op.create_index('ix_observations_user_abnormal', 'observations', ['user_id', 'is_abnormal'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_observations_user_abnormal', 'observations')
    op.drop_index('ix_observations_user_metric_observed', 'observations')
    op.drop_index('ix_reports_user_uploaded', 'reports')
    op.drop_index('ix_reports_doc_type', 'reports')
    op.drop_index('ix_reports_category', 'reports')
    
    # Remove columns from observations
    op.drop_column('observations', 'user_corrected')
    op.drop_column('observations', 'confidence')
    op.drop_column('observations', 'source')
    
    # Remove columns from reports
    op.drop_column('reports', 'extraction_source')
    op.drop_column('reports', 'classification_rules_matched')
    op.drop_column('reports', 'classification_confidence')
    op.drop_column('reports', 'doc_type')
    op.drop_column('reports', 'category')
    
    # Drop tables
    op.drop_index('ix_health_index_snapshots_user_created', 'health_index_snapshots')
    op.drop_table('health_index_snapshots')
    
    op.drop_index('ix_missing_data_tasks_status', 'missing_data_tasks')
    op.drop_index('ix_missing_data_tasks_user_document', 'missing_data_tasks')
    op.drop_table('missing_data_tasks')
    
    op.drop_index('ix_document_ocr_document_id', 'document_ocr')
    op.drop_table('document_ocr')
