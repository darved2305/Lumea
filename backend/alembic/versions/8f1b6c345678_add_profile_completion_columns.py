"""add profile completion columns

Revision ID: 8f1b6c345678
Revises: 7e0a5b234567
Create Date: 2025-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f1b6c345678'
down_revision: Union[str, None] = '7e0a5b234567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_completed and completed_at columns to user_profiles
    op.add_column('user_profiles', sa.Column('is_completed', sa.Boolean(), nullable=True, default=False))
    op.add_column('user_profiles', sa.Column('completed_at', sa.DateTime(), nullable=True))
    
    # Set default value for existing rows
    op.execute("UPDATE user_profiles SET is_completed = false WHERE is_completed IS NULL")


def downgrade() -> None:
    op.drop_column('user_profiles', 'completed_at')
    op.drop_column('user_profiles', 'is_completed')
