"""Add AI summary and comparison tables

Revision ID: 5c8a3e1f4567
Revises: 4b7c2e891234
Create Date: 2026-02-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5c8a3e1f4567'
down_revision: Union[str, Sequence[str], None] = '4b7c2e891234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI summary tables."""
    
    # Create report_ai_summaries table
    op.create_table('report_ai_summaries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('report_id', sa.UUID(), nullable=False),
        sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_ai_summaries_user_id', 'report_ai_summaries', ['user_id'], unique=False)
    op.create_index('ix_report_ai_summaries_report_id', 'report_ai_summaries', ['report_id'], unique=False)
    op.create_index('ix_report_ai_summaries_source_hash', 'report_ai_summaries', ['source_hash'], unique=False)
    
    # Create report_ai_comparisons table
    op.create_table('report_ai_comparisons',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('report_ids_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('comparison_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_ai_comparisons_user_id', 'report_ai_comparisons', ['user_id'], unique=False)
    op.create_index('ix_report_ai_comparisons_source_hash', 'report_ai_comparisons', ['source_hash'], unique=False)


def downgrade() -> None:
    """Drop AI summary tables."""
    op.drop_index('ix_report_ai_comparisons_source_hash', table_name='report_ai_comparisons')
    op.drop_index('ix_report_ai_comparisons_user_id', table_name='report_ai_comparisons')
    op.drop_table('report_ai_comparisons')
    
    op.drop_index('ix_report_ai_summaries_source_hash', table_name='report_ai_summaries')
    op.drop_index('ix_report_ai_summaries_report_id', table_name='report_ai_summaries')
    op.drop_index('ix_report_ai_summaries_user_id', table_name='report_ai_summaries')
    op.drop_table('report_ai_summaries')
