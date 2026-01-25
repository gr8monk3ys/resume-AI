"""fix_profile_user_id_not_null

Revision ID: a93ef862abc0
Revises: d12b0d5a45ef
Create Date: 2026-01-24 20:45:00.000000

This migration fixes a data integrity issue where Profile.user_id was
incorrectly nullable. Every profile MUST be associated with a user.

IMPORTANT: Before running this migration in production:
1. Verify there are no orphaned profiles (profiles with NULL user_id)
2. If orphaned profiles exist, either:
   - Delete them: DELETE FROM profiles WHERE user_id IS NULL;
   - Assign them to a user: UPDATE profiles SET user_id = <user_id> WHERE user_id IS NULL;

This migration will FAIL if orphaned profiles exist.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a93ef862abc0'
down_revision: Union[str, Sequence[str], None] = 'd12b0d5a45ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Make Profile.user_id NOT NULL.

    This ensures data integrity by requiring every profile to be
    associated with a user. The unique constraint already exists
    from the initial migration.
    """
    # First, check for orphaned profiles and handle them
    # This is done in a way that works with both SQLite and PostgreSQL
    connection = op.get_bind()

    # Check if any orphaned profiles exist
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM profiles WHERE user_id IS NULL")
    )
    orphan_count = result.scalar()

    if orphan_count > 0:
        # In production, you would typically want to handle this more gracefully
        # For now, we raise an error to prevent data loss
        raise RuntimeError(
            f"Cannot apply migration: {orphan_count} orphaned profile(s) found "
            f"with NULL user_id. Please clean up orphaned profiles before "
            f"running this migration. You can either:\n"
            f"  1. Delete them: DELETE FROM profiles WHERE user_id IS NULL;\n"
            f"  2. Assign them to a user: UPDATE profiles SET user_id = <user_id> WHERE user_id IS NULL;"
        )

    # Use batch mode for SQLite compatibility
    # SQLite doesn't support ALTER COLUMN directly, so Alembic recreates the table
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    """
    Revert Profile.user_id to nullable.

    This is provided for rollback purposes, but note that making
    a column nullable is generally safe and doesn't lose data.
    """
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            nullable=True,
        )
