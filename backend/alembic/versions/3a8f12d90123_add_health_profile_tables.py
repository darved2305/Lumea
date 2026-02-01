"""Add health profile tables

Revision ID: 3a8f12d90123
Revises: 2e594cf604c2
Create Date: 2026-02-01 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3a8f12d90123'
down_revision: Union[str, Sequence[str], None] = '2e594cf604c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add health profile tables."""
    
    # 1. user_profiles - core profile data (1 row per user)
    op.create_table('user_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        
        # Step 1: Basics
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('age_years', sa.Integer(), nullable=True),  # fallback if DOB unknown
        sa.Column('sex_at_birth', sa.String(20), nullable=True),  # male/female/intersex/prefer_not
        sa.Column('gender', sa.String(50), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        
        # Step 2: Body Measurements
        sa.Column('height_cm', sa.Float(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('waist_cm', sa.Float(), nullable=True),
        sa.Column('activity_level', sa.String(20), nullable=True),  # sedentary/moderate/active
        
        # Step 6: Lifestyle
        sa.Column('smoking', sa.String(20), nullable=True),  # never/former/current/prefer_not/unknown
        sa.Column('alcohol', sa.String(20), nullable=True),  # none/occasional/frequent/unknown
        sa.Column('sleep_hours_avg', sa.Float(), nullable=True),
        sa.Column('sleep_quality', sa.String(20), nullable=True),  # good/ok/poor/unknown
        sa.Column('exercise_minutes_per_week', sa.Integer(), nullable=True),
        sa.Column('diet_pattern', sa.String(20), nullable=True),  # veg/nonveg/mixed/unknown
        
        # Wizard state
        sa.Column('wizard_current_step', sa.Integer(), default=1),
        sa.Column('wizard_completed', sa.Boolean(), default=False),
        sa.Column('wizard_last_saved_at', sa.DateTime(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_user_profiles_user_id')
    )
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'], unique=True)
    
    # 2. profile_answers - flexible JSONB storage for any question answer
    op.create_table('profile_answers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('question_id', sa.String(100), nullable=False),  # e.g., "height_cm", "family_history_mother_diabetes"
        sa.Column('answer_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        # answer_data schema: { "value": any, "unit": str?, "unknown": bool, "skipped": bool }
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'question_id', name='uq_profile_answers_user_question')
    )
    op.create_index('ix_profile_answers_user_id', 'profile_answers', ['user_id'])
    op.create_index('ix_profile_answers_question_id', 'profile_answers', ['question_id'])
    
    # 3. profile_conditions - diagnosed conditions (normalized)
    op.create_table('profile_conditions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('condition_code', sa.String(50), nullable=False),  # diabetes, high_bp, etc.
        sa.Column('condition_name', sa.String(200), nullable=True),  # display name
        sa.Column('diagnosed_at', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'condition_code', name='uq_profile_conditions_user_condition')
    )
    op.create_index('ix_profile_conditions_user_id', 'profile_conditions', ['user_id'])
    
    # 4. profile_symptoms - recurring symptoms
    op.create_table('profile_symptoms',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('symptom_code', sa.String(50), nullable=False),
        sa.Column('symptom_name', sa.String(200), nullable=True),
        sa.Column('frequency', sa.String(50), nullable=True),  # daily/weekly/monthly/occasional
        sa.Column('severity', sa.String(20), nullable=True),  # mild/moderate/severe
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_profile_symptoms_user_id', 'profile_symptoms', ['user_id'])
    
    # 5. profile_medications - current medications
    op.create_table('profile_medications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('dose', sa.String(100), nullable=True),
        sa.Column('frequency', sa.String(100), nullable=True),  # once_daily, twice_daily, as_needed, etc.
        sa.Column('started_at', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_profile_medications_user_id', 'profile_medications', ['user_id'])
    
    # 6. profile_supplements - supplements/vitamins
    op.create_table('profile_supplements',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('dose', sa.String(100), nullable=True),
        sa.Column('frequency', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_profile_supplements_user_id', 'profile_supplements', ['user_id'])
    
    # 7. profile_allergies - allergies
    op.create_table('profile_allergies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('allergen', sa.String(200), nullable=False),
        sa.Column('allergy_type', sa.String(50), nullable=True),  # drug/food/environmental/other
        sa.Column('reaction', sa.String(500), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),  # mild/moderate/severe/life_threatening
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_profile_allergies_user_id', 'profile_allergies', ['user_id'])
    
    # 8. profile_family_history - family medical history
    op.create_table('profile_family_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('relative_type', sa.String(50), nullable=False),  # mother/father/sibling/grandparent_maternal/grandparent_paternal
        sa.Column('condition_code', sa.String(50), nullable=False),
        sa.Column('condition_name', sa.String(200), nullable=True),
        sa.Column('age_at_diagnosis', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_profile_family_history_user_id', 'profile_family_history', ['user_id'])
    
    # 9. profile_genetic_tests - genetic test results
    op.create_table('profile_genetic_tests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('mutation_name', sa.String(100), nullable=False),  # BRCA1, BRCA2, etc.
        sa.Column('result', sa.String(50), nullable=True),  # positive/negative/variant_uncertain
        sa.Column('test_date', sa.Date(), nullable=True),
        sa.Column('lab_name', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_profile_genetic_tests_user_id', 'profile_genetic_tests', ['user_id'])
    
    # 10. derived_features - computed values (BMI, risk scores, completeness)
    op.create_table('derived_features',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('feature_name', sa.String(100), nullable=False),  # bmi, bmi_category, age_computed, completeness_score, etc.
        sa.Column('feature_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        # feature_value can be: { "value": 24.5 } or { "value": "normal" } or { "score": 85, "missing": ["weight_kg"] }
        sa.Column('computed_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=True),  # for time-sensitive features
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'feature_name', name='uq_derived_features_user_feature')
    )
    op.create_index('ix_derived_features_user_id', 'derived_features', ['user_id'])
    op.create_index('ix_derived_features_feature_name', 'derived_features', ['feature_name'])
    
    # 11. profile_recommendations - generated recommendations with evidence
    op.create_table('profile_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('recommendation_type', sa.String(50), nullable=False),  # lifestyle/screening/followup/urgent
        sa.Column('category', sa.String(50), nullable=True),  # nutrition/exercise/sleep/medical
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), default=5),  # 1-10, 1 being highest
        sa.Column('evidence_jsonb', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # evidence_jsonb: { "source_fields": [...], "rules_triggered": [...], "confidence": 0.85 }
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('dismissed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('ix_profile_recommendations_user_id', 'profile_recommendations', ['user_id'])
    op.create_index('ix_profile_recommendations_type', 'profile_recommendations', ['recommendation_type'])
    op.create_index('ix_profile_recommendations_active', 'profile_recommendations', ['is_active'])


def downgrade() -> None:
    """Downgrade schema - remove health profile tables."""
    op.drop_index('ix_profile_recommendations_active', table_name='profile_recommendations')
    op.drop_index('ix_profile_recommendations_type', table_name='profile_recommendations')
    op.drop_index('ix_profile_recommendations_user_id', table_name='profile_recommendations')
    op.drop_table('profile_recommendations')
    
    op.drop_index('ix_derived_features_feature_name', table_name='derived_features')
    op.drop_index('ix_derived_features_user_id', table_name='derived_features')
    op.drop_table('derived_features')
    
    op.drop_index('ix_profile_genetic_tests_user_id', table_name='profile_genetic_tests')
    op.drop_table('profile_genetic_tests')
    
    op.drop_index('ix_profile_family_history_user_id', table_name='profile_family_history')
    op.drop_table('profile_family_history')
    
    op.drop_index('ix_profile_allergies_user_id', table_name='profile_allergies')
    op.drop_table('profile_allergies')
    
    op.drop_index('ix_profile_supplements_user_id', table_name='profile_supplements')
    op.drop_table('profile_supplements')
    
    op.drop_index('ix_profile_medications_user_id', table_name='profile_medications')
    op.drop_table('profile_medications')
    
    op.drop_index('ix_profile_symptoms_user_id', table_name='profile_symptoms')
    op.drop_table('profile_symptoms')
    
    op.drop_index('ix_profile_conditions_user_id', table_name='profile_conditions')
    op.drop_table('profile_conditions')
    
    op.drop_index('ix_profile_answers_question_id', table_name='profile_answers')
    op.drop_index('ix_profile_answers_user_id', table_name='profile_answers')
    op.drop_table('profile_answers')
    
    op.drop_index('ix_user_profiles_user_id', table_name='user_profiles')
    op.drop_table('user_profiles')
