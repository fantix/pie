import binascii
import hashlib
import os
from datetime import datetime, timedelta
from enum import Enum

import sqlalchemy as sa
from asyncpg import UniqueViolationError
from gino.orm.json_support import StringProperty
from sqlalchemy.dialects.postgresql import JSONB

from ..db import Model
from ..utils import retry_on


class User(Model):
    __tablename__ = 'users'

    id = sa.Column(sa.BigInteger(), primary_key=True)
    email = sa.Column(sa.Unicode(), index=True, unique=True)
    password = sa.Column(sa.Unicode())
    profile = sa.Column(JSONB(), nullable=False, server_default='{}')


class Token(Model):
    __tablename__ = 'tokens'

    class Actions(Enum):
        login = 'login'

    id = sa.Column(sa.BigInteger(), primary_key=True)
    selector = sa.Column(sa.Unicode(), nullable=False, index=True, unique=True)
    validator = sa.Column(sa.Unicode(), nullable=False)
    created_at = sa.Column(sa.DateTime(), nullable=False)
    expires_at = sa.Column(sa.DateTime(), nullable=False)
    used_at = sa.Column(sa.DateTime())
    profile = sa.Column(JSONB(), nullable=False, server_default='{}')
    action = StringProperty()
    email = StringProperty()

    @classmethod
    def _split(cls, token):
        return token[:32], hashlib.shake_128(
            binascii.unhexlify(token[32:])).hexdigest(16)

    @classmethod
    @retry_on(UniqueViolationError)
    async def new(cls, ttl=timedelta(minutes=10), **payload):
        rv = hashlib.sha3_256(os.urandom(32)).hexdigest()
        selector, validator = cls._split(rv)
        now = datetime.utcnow()
        await cls.create(selector=selector, validator=validator,
                         created_at=now, expires_at=now + ttl, **payload)
        return rv

    @classmethod
    async def verify(cls, token):
        selector, validator = cls._split(token)
        rv = await cls.query.where(
            cls.selector == selector,
        ).with_for_update().execute().first()
        if rv and (rv.validator != validator or
                   rv.used_at or
                   datetime.utcnow() > rv.expires_at):
            rv = None
        return rv

    async def use(self):
        await self.update(used_at=datetime.utcnow()).apply()
