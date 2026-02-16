"""add_visa_salary_remote_fields

Revision ID: b4e7f1a2c3d5
Revises: a93ef862abc0
Create Date: 2026-02-16 00:00:00.000000

Adds H-1B visa sponsorship tracking, salary range, and remote work type
columns to the job_applications table. These fields support filtering
job applications by sponsorship availability, compensation range, and
work arrangement -- a competitive feature for international job seekers.

New columns:
- visa_sponsorship (String): "Yes", "No", or "Unknown"
- salary_min (Integer): Minimum salary in the range
- salary_max (Integer): Maximum salary in the range
- salary_currency (String): Currency code, defaults to "USD"
- remote_type (String): "Remote", "Hybrid", "On-site", or "Flexible"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e7f1a2c3d5'
down_revision: Union[str, Sequence[str], None] = 'a93ef862abc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add visa sponsorship, salary range, and remote type columns
    to job_applications table.

    Uses batch mode for SQLite compatibility. Includes indexes on
    visa_sponsorship and remote_type for efficient filtering, and a
    composite index on (profile_id, visa_sponsorship) for the common
    query pattern of filtering a user's jobs by sponsorship status.
    """
    with op.batch_alter_table('job_applications', schema=None) as batch_op:
        # Visa sponsorship tracking
        batch_op.add_column(
            sa.Column('visa_sponsorship', sa.String(), nullable=True)
        )

        # Salary range tracking
        batch_op.add_column(
            sa.Column('salary_min', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('salary_max', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('salary_currency', sa.String(), nullable=True, server_default='USD')
        )

        # Remote work type
        batch_op.add_column(
            sa.Column('remote_type', sa.String(), nullable=True)
        )

        # Indexes for common filter queries
        batch_op.create_index(
            'ix_job_applications_visa_sponsorship',
            ['visa_sponsorship'],
            unique=False,
        )
        batch_op.create_index(
            'ix_job_applications_remote_type',
            ['remote_type'],
            unique=False,
        )

    # Composite index for filtering a user's jobs by visa sponsorship
    op.create_index(
        'ix_job_applications_profile_visa',
        'job_applications',
        ['profile_id', 'visa_sponsorship'],
        unique=False,
    )


def downgrade() -> None:
    """
    Remove visa sponsorship, salary range, and remote type columns
    from job_applications table.
    """
    # Drop composite index first
    op.drop_index('ix_job_applications_profile_visa', table_name='job_applications')

    with op.batch_alter_table('job_applications', schema=None) as batch_op:
        batch_op.drop_index('ix_job_applications_remote_type')
        batch_op.drop_index('ix_job_applications_visa_sponsorship')
        batch_op.drop_column('remote_type')
        batch_op.drop_column('salary_currency')
        batch_op.drop_column('salary_max')
        batch_op.drop_column('salary_min')
        batch_op.drop_column('visa_sponsorship')
