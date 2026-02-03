"""Add medicines feature tables

Revision ID: 6d9e4f012345
Revises: 5342eca742c1
Create Date: 2026-02-03 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6d9e4f012345'
down_revision: Union[str, Sequence[str], None] = '5342eca742c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create medicines feature tables."""
    
    # Generic Catalog - seeded from Jan Aushadhi/PMBI data
    op.create_table(
        'generic_catalog',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('product_name', sa.String(500), nullable=False),
        sa.Column('salt', sa.String(500), nullable=False, index=True),
        sa.Column('strength', sa.String(100), nullable=False),
        sa.Column('form', sa.String(100), nullable=False),  # tablet/capsule/syrup/injection
        sa.Column('release_type', sa.String(50), nullable=True),  # SR/ER/CR/Normal/null
        sa.Column('mrp', sa.Numeric(10, 2), nullable=True),
        sa.Column('manufacturer', sa.String(300), nullable=True),
        sa.Column('source', sa.String(50), nullable=False, default='jan_aushadhi'),  # jan_aushadhi/pmbi/other
        sa.Column('is_jan_aushadhi', sa.Boolean, default=False, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_generic_catalog_salt_strength_form', 'generic_catalog', ['salt', 'strength', 'form'])
    op.create_index('ix_generic_catalog_product_name', 'generic_catalog', ['product_name'])
    
    # User Saved Medicines
    op.create_table(
        'user_saved_medicines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('original_name', sa.String(500), nullable=True),
        sa.Column('salt', sa.String(500), nullable=False),
        sa.Column('strength', sa.String(100), nullable=False),
        sa.Column('form', sa.String(100), nullable=False),
        sa.Column('release_type', sa.String(50), nullable=True),
        sa.Column('schedule_json', postgresql.JSONB, nullable=True),  # dosage schedule
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Substitute Queries - for analytics and caching
    op.create_table(
        'substitute_queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('query_raw', sa.Text, nullable=False),
        sa.Column('normalized_json', postgresql.JSONB, nullable=True),
        sa.Column('results_json', postgresql.JSONB, nullable=True),
        sa.Column('results_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Pharmacy Clicks - analytics for pharmacy visits
    op.create_table(
        'pharmacy_clicks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('place_id', sa.String(300), nullable=False),
        sa.Column('place_name', sa.String(500), nullable=True),
        sa.Column('mode', sa.String(50), nullable=False),  # pharmacy/janaushadhi
        sa.Column('created_at', sa.DateTime, server_default=sa.text('NOW()'), nullable=False),
    )
    
    # User Location Consent
    op.create_table(
        'user_location_consent',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('consent', sa.Boolean, default=False, nullable=False),
        sa.Column('updated_at', sa.DateTime, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
    )


def downgrade() -> None:
    """Drop medicines feature tables."""
    op.drop_table('user_location_consent')
    op.drop_table('pharmacy_clicks')
    op.drop_table('substitute_queries')
    op.drop_table('user_saved_medicines')
    op.drop_index('ix_generic_catalog_product_name', 'generic_catalog')
    op.drop_index('ix_generic_catalog_salt_strength_form', 'generic_catalog')
    op.drop_table('generic_catalog')
