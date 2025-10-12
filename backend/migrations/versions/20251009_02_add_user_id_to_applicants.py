from alembic import op
import sqlalchemy as sa

revision = '20251009_02'
down_revision = '20251009_01'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('applicants', sa.Column('user_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('applicants', 'user_id')
