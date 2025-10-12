"""recreate users table

Revision ID: fe22d4265803
Revises: 90d6629f19d9
Create Date: 2025-10-12 14:03:55.439359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fe22d4265803'
down_revision: Union[str, Sequence[str], None] = '90d6629f19d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    userrole = postgresql.ENUM('applicant', 'recruiter', name='userrole', create_type=False)
    userrole.create(op.get_bind(), checkfirst=True)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', userrole, nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
    userrole = postgresql.ENUM('applicant', 'recruiter', name='userrole', create_type=False)
    userrole.drop(op.get_bind(), checkfirst=True)
