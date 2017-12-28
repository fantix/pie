import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from ..db import Model


class User(Model):
    __tablename__ = 'users'

    id = sa.Column(sa.BigInteger(), primary_key=True)
    profile = sa.Column(JSONB(), nullable=False, server_default='{}')
