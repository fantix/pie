"""tokens

Revision ID: b96aeefbf221
Revises: 91ba4abeb405
Create Date: 2018-01-12 12:08:01.236633

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b96aeefbf221'
down_revision = '91ba4abeb405'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tokens',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('selector', sa.Unicode(), nullable=False),
        sa.Column('validator', sa.Unicode(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('profile', postgresql.JSONB(astext_type=sa.Text()),
                  server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tokens_selector'), 'tokens', ['selector'],
                    unique=True)
    op.add_column('users', sa.Column('email', sa.Unicode(), nullable=True))
    op.add_column('users', sa.Column('password', sa.Unicode(), nullable=True))
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_column('users', 'password')
    op.drop_column('users', 'email')
    op.drop_index(op.f('ix_tokens_selector'), table_name='tokens')
    op.drop_table('tokens')
