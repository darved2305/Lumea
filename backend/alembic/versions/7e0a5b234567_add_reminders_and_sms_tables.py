"""Add reminders and SMS tables

Revision ID: 7e0a5b234567
Revises: 6d9e4f012345
Create Date: 2026-02-04 10:00:00.000000

Adds:
- is_completed, completed_at, phone_number to user_profiles
- reminders table for scheduled reminders
- reminder_events table for SMS/notification delivery logs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7e0a5b234567'
down_revision: Union[str, Sequence[str], None] = '6d9e4f012345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add reminders system tables."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())
    
    # 1. Add new columns to user_profiles table
    if 'user_profiles' in existing_tables:
        existing_columns = {col['name'] for col in insp.get_columns('user_profiles')}
        
        if 'is_completed' not in existing_columns:
            op.add_column('user_profiles', sa.Column('is_completed', sa.Boolean(), server_default='false', nullable=False))
        
        if 'completed_at' not in existing_columns:
            op.add_column('user_profiles', sa.Column('completed_at', sa.DateTime(), nullable=True))
        
        if 'phone_number' not in existing_columns:
            op.add_column('user_profiles', sa.Column('phone_number', sa.String(20), nullable=True))
    
    # 2. Create reminders table
    if 'reminders' not in existing_tables:
        op.create_table(
            'reminders',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            
            # Reminder details
            sa.Column('type', sa.String(50), nullable=False),  # medicine|hydration|sleep|checkup|custom
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('message', sa.Text(), nullable=True),
            
            # Schedule configuration
            sa.Column('schedule_type', sa.String(30), nullable=False),  # fixed_times|interval|cron
            sa.Column('schedule_json', postgresql.JSONB(), nullable=False),
            # schedule_json examples:
            # fixed_times: {"times": ["08:00", "14:00", "20:00"]}
            # interval: {"interval_minutes": 120, "start_time": "08:00", "end_time": "22:00"}
            # cron: {"cron": "0 9 * * *"}
            
            # Timezone (for proper scheduling)
            sa.Column('timezone', sa.String(50), server_default='Asia/Kolkata', nullable=False),
            
            # Execution tracking
            sa.Column('next_run_at', sa.DateTime(), nullable=True, index=True),
            sa.Column('last_run_at', sa.DateTime(), nullable=True),
            
            # Status
            sa.Column('is_enabled', sa.Boolean(), server_default='true', nullable=False),
            
            # Delivery channel
            sa.Column('channel', sa.String(20), server_default='sms', nullable=False),  # sms|in_app|push|email
            
            # Medicine-specific fields (optional)
            sa.Column('medicine_id', postgresql.UUID(as_uuid=True), nullable=True),  # Link to user_saved_medicines
            sa.Column('medicine_name', sa.String(200), nullable=True),
            
            # Timestamps
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), onupdate=sa.text('NOW()'), nullable=False),
        )
        op.create_index('ix_reminders_user_enabled', 'reminders', ['user_id', 'is_enabled'])
        op.create_index('ix_reminders_next_run', 'reminders', ['next_run_at', 'is_enabled'])
    
    # 3. Create reminder_events table (delivery log)
    if 'reminder_events' not in existing_tables:
        op.create_table(
            'reminder_events',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
            sa.Column('reminder_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reminders.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            
            # Delivery details
            sa.Column('sent_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
            sa.Column('status', sa.String(20), nullable=False),  # sent|failed|mocked|skipped
            sa.Column('provider', sa.String(30), nullable=False),  # twilio|mock|in_app
            sa.Column('provider_response', postgresql.JSONB(), nullable=True),  # API response for debugging
            
            # Message content (for audit)
            sa.Column('message_sent', sa.Text(), nullable=True),
            sa.Column('phone_number', sa.String(20), nullable=True),  # Recipient (masked for privacy in logs)
            
            # Error tracking
            sa.Column('error_message', sa.Text(), nullable=True),
        )
        op.create_index('ix_reminder_events_sent_at', 'reminder_events', ['sent_at'])
        op.create_index('ix_reminder_events_status', 'reminder_events', ['status'])


def downgrade() -> None:
    """Downgrade schema - remove reminders system tables."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_tables = set(insp.get_table_names())
    
    # Drop tables in reverse order (respect FK constraints)
    if 'reminder_events' in existing_tables:
        op.drop_index('ix_reminder_events_status', 'reminder_events')
        op.drop_index('ix_reminder_events_sent_at', 'reminder_events')
        op.drop_table('reminder_events')
    
    if 'reminders' in existing_tables:
        op.drop_index('ix_reminders_next_run', 'reminders')
        op.drop_index('ix_reminders_user_enabled', 'reminders')
        op.drop_table('reminders')
    
    # Remove columns from user_profiles
    if 'user_profiles' in existing_tables:
        existing_columns = {col['name'] for col in insp.get_columns('user_profiles')}
        
        if 'phone_number' in existing_columns:
            op.drop_column('user_profiles', 'phone_number')
        if 'completed_at' in existing_columns:
            op.drop_column('user_profiles', 'completed_at')
        if 'is_completed' in existing_columns:
            op.drop_column('user_profiles', 'is_completed')
