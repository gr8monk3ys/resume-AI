"""initial_schema

Revision ID: d12b0d5a45ef
Revises:
Create Date: 2026-01-24 20:39:33.407449

Initial migration that captures the current database schema.
This establishes a baseline for the ResuBoost AI application.

Tables created:
- users: User authentication
- profiles: User profile information
- resumes: Resume storage with versioning
- job_applications: Job application tracker
- cover_letters: Generated cover letters
- career_journal: Career journal entries
- job_alerts: Job alert configurations
- company_filters: Company blacklist/whitelist
- keyword_filters: Keyword filtering rules
- application_questions: Template answers for common questions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd12b0d5a45ef'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for ResuBoost AI."""

    # Users table - authentication
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('token_version', sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Profiles table - user profile information
    # NOTE: user_id is currently nullable but should be NOT NULL.
    # This will be fixed in a subsequent migration.
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),  # Will be fixed in next migration
        sa.Column('name', sa.String(), nullable=False, default='New User'),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('linkedin', sa.String(), nullable=True),
        sa.Column('github', sa.String(), nullable=True),
        sa.Column('portfolio', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index(op.f('ix_profiles_id'), 'profiles', ['id'], unique=False)

    # Resumes table - resume storage with versioning
    op.create_table(
        'resumes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('version_name', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('ats_score', sa.Integer(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resumes_id'), 'resumes', ['id'], unique=False)
    op.create_index(op.f('ix_resumes_profile_id'), 'resumes', ['profile_id'], unique=False)

    # Job Applications table - job application tracker
    op.create_table(
        'job_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('position', sa.String(), nullable=False),
        sa.Column('job_description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='Bookmarked'),
        sa.Column('application_date', sa.Date(), nullable=True),
        sa.Column('deadline', sa.Date(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('job_url', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('recruiter_name', sa.String(), nullable=True),
        sa.Column('recruiter_email', sa.String(), nullable=True),
        sa.Column('recruiter_linkedin', sa.String(), nullable=True),
        sa.Column('recruiter_phone', sa.String(), nullable=True),
        sa.Column('referral_name', sa.String(), nullable=True),
        sa.Column('referral_relationship', sa.String(), nullable=True),
        sa.Column('application_source', sa.String(), nullable=True),
        sa.Column('response_date', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('resume_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_applications_id'), 'job_applications', ['id'], unique=False)
    op.create_index(op.f('ix_job_applications_profile_id'), 'job_applications', ['profile_id'], unique=False)
    op.create_index(op.f('ix_job_applications_status'), 'job_applications', ['status'], unique=False)
    op.create_index(op.f('ix_job_applications_application_date'), 'job_applications', ['application_date'], unique=False)
    op.create_index(op.f('ix_job_applications_updated_at'), 'job_applications', ['updated_at'], unique=False)
    op.create_index(op.f('ix_job_applications_application_source'), 'job_applications', ['application_source'], unique=False)
    # Composite indexes for common query patterns
    op.create_index('ix_job_applications_profile_status', 'job_applications', ['profile_id', 'status'], unique=False)
    op.create_index('ix_job_applications_profile_updated', 'job_applications', ['profile_id', 'updated_at'], unique=False)

    # Cover Letters table - generated cover letters
    op.create_table(
        'cover_letters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('job_application_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['job_application_id'], ['job_applications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cover_letters_id'), 'cover_letters', ['id'], unique=False)
    op.create_index(op.f('ix_cover_letters_profile_id'), 'cover_letters', ['profile_id'], unique=False)

    # Career Journal table - career journal entries
    op.create_table(
        'career_journal',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('achievement_date', sa.Date(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_career_journal_id'), 'career_journal', ['id'], unique=False)
    op.create_index(op.f('ix_career_journal_profile_id'), 'career_journal', ['profile_id'], unique=False)

    # Job Alerts table - job alert configurations
    op.create_table(
        'job_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column('companies', sa.Text(), nullable=True),
        sa.Column('locations', sa.Text(), nullable=True),
        sa.Column('job_types', sa.Text(), nullable=True),
        sa.Column('min_salary', sa.Integer(), nullable=True),
        sa.Column('exclude_keywords', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.Column('last_notified', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_alerts_id'), 'job_alerts', ['id'], unique=False)
    op.create_index(op.f('ix_job_alerts_user_id'), 'job_alerts', ['user_id'], unique=False)
    op.create_index(op.f('ix_job_alerts_is_active'), 'job_alerts', ['is_active'], unique=False)

    # Company Filters table - company blacklist/whitelist
    op.create_table(
        'company_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('filter_type', sa.Enum('BLACKLIST', 'WHITELIST', name='companyfiltertype'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_company_filters_id'), 'company_filters', ['id'], unique=False)
    op.create_index(op.f('ix_company_filters_user_id'), 'company_filters', ['user_id'], unique=False)
    op.create_index(op.f('ix_company_filters_company_name'), 'company_filters', ['company_name'], unique=False)

    # Keyword Filters table - keyword filtering rules
    op.create_table(
        'keyword_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(255), nullable=False),
        sa.Column('filter_type', sa.Enum('EXCLUDE', 'REQUIRE', name='keywordfiltertype'), nullable=False),
        sa.Column('applies_to', sa.Enum('TITLE', 'DESCRIPTION', 'BOTH', name='keywordappliesto'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_keyword_filters_id'), 'keyword_filters', ['id'], unique=False)
    op.create_index(op.f('ix_keyword_filters_user_id'), 'keyword_filters', ['user_id'], unique=False)
    op.create_index(op.f('ix_keyword_filters_keyword'), 'keyword_filters', ['keyword'], unique=False)

    # Application Questions table - template answers for common questions
    op.create_table(
        'application_questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_pattern', sa.String(500), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('question_type', sa.Enum('TEXT', 'NUMBER', 'SELECT', 'BOOLEAN', name='questiontype'), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_application_questions_id'), 'application_questions', ['id'], unique=False)
    op.create_index(op.f('ix_application_questions_user_id'), 'application_questions', ['user_id'], unique=False)
    op.create_index(op.f('ix_application_questions_question_pattern'), 'application_questions', ['question_pattern'], unique=False)
    op.create_index(op.f('ix_application_questions_category'), 'application_questions', ['category'], unique=False)


def downgrade() -> None:
    """Drop all tables in reverse order of creation."""
    # Drop tables with foreign key dependencies first
    op.drop_index(op.f('ix_application_questions_category'), table_name='application_questions')
    op.drop_index(op.f('ix_application_questions_question_pattern'), table_name='application_questions')
    op.drop_index(op.f('ix_application_questions_user_id'), table_name='application_questions')
    op.drop_index(op.f('ix_application_questions_id'), table_name='application_questions')
    op.drop_table('application_questions')

    op.drop_index(op.f('ix_keyword_filters_keyword'), table_name='keyword_filters')
    op.drop_index(op.f('ix_keyword_filters_user_id'), table_name='keyword_filters')
    op.drop_index(op.f('ix_keyword_filters_id'), table_name='keyword_filters')
    op.drop_table('keyword_filters')

    op.drop_index(op.f('ix_company_filters_company_name'), table_name='company_filters')
    op.drop_index(op.f('ix_company_filters_user_id'), table_name='company_filters')
    op.drop_index(op.f('ix_company_filters_id'), table_name='company_filters')
    op.drop_table('company_filters')

    op.drop_index(op.f('ix_job_alerts_is_active'), table_name='job_alerts')
    op.drop_index(op.f('ix_job_alerts_user_id'), table_name='job_alerts')
    op.drop_index(op.f('ix_job_alerts_id'), table_name='job_alerts')
    op.drop_table('job_alerts')

    op.drop_index(op.f('ix_career_journal_profile_id'), table_name='career_journal')
    op.drop_index(op.f('ix_career_journal_id'), table_name='career_journal')
    op.drop_table('career_journal')

    op.drop_index(op.f('ix_cover_letters_profile_id'), table_name='cover_letters')
    op.drop_index(op.f('ix_cover_letters_id'), table_name='cover_letters')
    op.drop_table('cover_letters')

    op.drop_index('ix_job_applications_profile_updated', table_name='job_applications')
    op.drop_index('ix_job_applications_profile_status', table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_application_source'), table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_updated_at'), table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_application_date'), table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_status'), table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_profile_id'), table_name='job_applications')
    op.drop_index(op.f('ix_job_applications_id'), table_name='job_applications')
    op.drop_table('job_applications')

    op.drop_index(op.f('ix_resumes_profile_id'), table_name='resumes')
    op.drop_index(op.f('ix_resumes_id'), table_name='resumes')
    op.drop_table('resumes')

    op.drop_index(op.f('ix_profiles_id'), table_name='profiles')
    op.drop_table('profiles')

    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')

    # Drop enums (only needed for PostgreSQL)
    op.execute("DROP TYPE IF EXISTS questiontype")
    op.execute("DROP TYPE IF EXISTS keywordappliesto")
    op.execute("DROP TYPE IF EXISTS keywordfiltertype")
    op.execute("DROP TYPE IF EXISTS companyfiltertype")
