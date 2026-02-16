"""add_salary_period_column

Revision ID: c7d3e9f4a1b8
Revises: b4e7f1a2c3d5
Create Date: 2026-02-16 12:00:00.000000

Adds the salary_period column to the job_applications table. This column
tracks whether a salary figure is yearly, monthly, or hourly, enabling
accurate salary comparisons across job applications. Defaults to "yearly"
for existing rows.

New column:
- salary_period (String): "yearly", "monthly", or "hourly"

This migration follows b4e7f1a2c3d5 which adds visa_sponsorship,
salary_min/max/currency, and remote_type.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d3e9f4a1b8'
down_revision: Union[str, Sequence[str], None] = 'b4e7f1a2c3d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add salary_period column to job_applications table.

    Uses batch mode for SQLite compatibility. The column defaults to
    "yearly" so that existing salary data (from salary_min/max/currency)
    is interpreted with a sensible default period.
    """
    with op.batch_alter_table('job_applications', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('salary_period', sa.String(), nullable=True, server_default='yearly')
        )


def downgrade() -> None:
    """
    Remove salary_period column from job_applications table.
    """
    with op.batch_alter_table('job_applications', schema=None) as batch_op:
        batch_op.drop_column('salary_period')
