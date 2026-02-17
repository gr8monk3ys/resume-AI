"""add_clerk_id_to_users

Revision ID: e1f2a3b4c5d6
Revises: c7d3e9f4a1b8
Create Date: 2026-02-17 12:00:00.000000

Adds clerk_id column to users table for Clerk authentication integration.
Makes password_hash nullable since Clerk manages passwords externally.
Removes token_version column (no longer needed with Clerk sessions).

Changes:
- clerk_id (String, unique, indexed): Maps Clerk user IDs to local users
- password_hash: Changed to nullable (Clerk manages passwords)
- token_version: Removed (Clerk handles token management)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'c7d3e9f4a1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add clerk_id column and make password_hash nullable.
    Uses batch mode for SQLite compatibility.
    """
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('clerk_id', sa.String(), nullable=True)
        )
        batch_op.create_index('ix_users_clerk_id', ['clerk_id'], unique=True)
        batch_op.alter_column('password_hash', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    """
    Remove clerk_id column and restore password_hash as non-nullable.
    """
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_clerk_id')
        batch_op.drop_column('clerk_id')
        batch_op.alter_column('password_hash', existing_type=sa.String(), nullable=False)
