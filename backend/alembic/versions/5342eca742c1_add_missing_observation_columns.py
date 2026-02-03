"""add_missing_observation_columns

Revision ID: 5342eca742c1
Revises: 5c8a3e1f4567
Create Date: 2026-02-03 08:34:00.187387

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5342eca742c1'
down_revision: Union[str, Sequence[str], None] = '5c8a3e1f4567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to observations table."""
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def _has_column(table: str, column: str) -> bool:
        try:
            return column in {c["name"] for c in insp.get_columns(table)}
        except Exception:
            return False

    # Add columns that exist in model but were missing from earlier migrations
    if not _has_column('observations', 'flag'):
        op.add_column('observations', sa.Column('flag', sa.String(), nullable=True))
    if not _has_column('observations', 'display_name'):
        op.add_column('observations', sa.Column('display_name', sa.String(), nullable=True))
    if not _has_column('observations', 'raw_line'):
        op.add_column('observations', sa.Column('raw_line', sa.Text(), nullable=True))
    if not _has_column('observations', 'page_num'):
        op.add_column('observations', sa.Column('page_num', sa.Integer(), nullable=True))
    
    # Also add extraction_method and page_stats to reports table if missing
    if not _has_column('reports', 'extraction_method'):
        op.add_column('reports', sa.Column('extraction_method', sa.String(), nullable=True))
    if not _has_column('reports', 'page_stats'):
        op.add_column('reports', sa.Column('page_stats', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove added columns."""
    op.drop_column('reports', 'page_stats')
    op.drop_column('reports', 'extraction_method')
    op.drop_column('observations', 'page_num')
    op.drop_column('observations', 'raw_line')
    op.drop_column('observations', 'display_name')
    op.drop_column('observations', 'flag')
