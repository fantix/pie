"""users

Revision ID: 91ba4abeb405
Revises: 
Create Date: 2017-12-28 12:00:29.609541

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '91ba4abeb405'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('profile', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('users')
