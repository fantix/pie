import binascii
import functools
import hashlib
import itertools
import os
import time

import aioredis

from . import base


DATA = b'\x00'
VALIDATOR = b'\x01'
NONCE = b'\x02'
NONCE_REPR = 'string.char(0x02)'
DECODERS = {
    b'\x10': lambda data: data,
    b'\x11': lambda data: data.decode('utf-8'),
    b'\x12': lambda data: int(data),
    b'\x13': lambda data: float(data),
    b'\x14': lambda data: data in {b'1', b'yes', b'true', b'True'},
}
ENCODERS = {
    bytes: (b'\x10', lambda data: data),
    str: (b'\x11', lambda data: data.encode('utf-8')),
    int: (b'\x12', lambda data: str(data).encode('utf-8')),
    float: (b'\x13', lambda data: str(data).encode('utf-8')),
    bool: (b'\x14', lambda data: b'1' if data else b'0'),
}


class NoScriptError(aioredis.ReplyError):
    MATCH_REPLY = 'NOSCRIPT'


class RetryError(aioredis.ReplyError):
    MATCH_REPLY = 'RETRY Hash collision'


class ConcurrentUpdateError(aioredis.ReplyError):
    MATCH_REPLY = 'RACE Concurrent update'


def script(m):
    text = m(None)
    sha1 = hashlib.sha1(text.encode('utf-8')).hexdigest()

    # noinspection PyDefaultArgument
    @functools.wraps(m)
    async def wrapper(self, keys=[], args=[]):
        try:
            return await self._app.redis.evalsha(sha1, keys, args)
        except NoScriptError:
            return await self._app.redis.eval(text, keys, args)
    return wrapper


def retried(m):
    @functools.wraps(m)
    async def wrapper(*args, **kwargs):
        for count in range(2):
            try:
                return await m(*args, **kwargs)
            except RetryError:
                if count > 0:
                    raise
        assert False
    return wrapper


class Session(base.Session):
    nonce_len = 8

    def __init__(self, request, using_cookie=False):
        super().__init__(request, using_cookie)
        self._nonce = None

    async def _load(self):
        selector, validator = self._split(self._session_id)
        data = await self._app.redis.hgetall(selector)
        deadline = float(data.get(validator, 0))
        now = time.time()
        if now < deadline:
            should_refresh = self._using_cookie and \
                             deadline - now < self.refresh_threshold
            rv = {}
            for key, value in data.items():
                key_type = key[:1]
                if key_type == DATA:
                    decoder = DECODERS.get(value[:1])
                    rv[key[1:].decode('utf-8')] = decoder(value[1:])
                elif key_type == VALIDATOR:
                    value = float(value)
                    if now > value:
                        self._to_del.add(key)
                    elif now + self.ttl - value < self.refresh_wait:
                        should_refresh = False
                elif key_type == NONCE:
                    self._nonce = value
            self._should_refresh = should_refresh
            return rv

    def _encode(self, extra_values: dict=None) -> list:
        values = {}
        for key, value in self._values.items():
            if key in self._values_changed:
                key_type, encoder = ENCODERS[type(value)]
                values[DATA + key.encode('utf-8')] = key_type + encoder(value)
        if extra_values:
            values.update(extra_values)
        return list(itertools.chain.from_iterable(values.items()))

    def _get_deadline(self):
        return time.time() + self.ttl

    def _make_nonce(self):
        return os.urandom(self.nonce_len)

    def _get_del(self):
        rv = []
        for key in self._to_del:
            if isinstance(key, str):
                key = DATA + key.encode('utf-8')
            rv.append(key)
        return rv

    def _split(self, session_id):
        selector = self.cookie_name.encode('utf-8') + b':' + \
                   binascii.unhexlify(session_id[:32])
        validator = VALIDATOR + hashlib.shake_128(binascii.unhexlify(
            session_id[32:])).digest(16)
        return selector, validator

    @script
    def _create_session(self):
        return f'''\
local rv
if (redis.call('EXISTS', KEYS[1]) == 0)
then
    rv = redis.call('HMSET', KEYS[1], unpack(ARGV))
    redis.call('PEXPIREAT', KEYS[1], KEYS[2])
else
    rv = {{err = '{RetryError.MATCH_REPLY}'}}
end
return rv
'''

    @retried
    async def _new_session(self):
        rv = hashlib.sha3_256(os.urandom(32)).hexdigest()
        selector, validator = self._split(rv)
        new_nonce = self._make_nonce()
        ts = self._get_deadline()
        # noinspection PyUnresolvedReferences
        await self._create_session([selector, int(ts * 1000)], self._encode(
            {validator: str(ts).encode('utf-8'), NONCE: new_nonce}))
        self._nonce = new_nonce
        self._values_changed.clear()
        self._cookie_deadline = ts
        return rv

    @script
    def _update_with_new_validator(self):
        return f'''\
local rv
if (redis.call('HGET', KEYS[1], {NONCE_REPR}) ~= KEYS[6])
then
    rv = {{err = '{ConcurrentUpdateError.MATCH_REPLY}'}}
elseif (redis.call('HSETNX', KEYS[1], KEYS[2], KEYS[3]) == 0)
then
    rv = {{err = '{RetryError.MATCH_REPLY}'}}
else
    rv = redis.call('HMSET', KEYS[1], unpack(ARGV, KEYS[5] + 1))
    if (KEYS[5] ~= '0')
    then
        redis.call('HDEL', KEYS[1], unpack(ARGV, 1, KEYS[5]))
    end
    redis.call('PEXPIREAT', KEYS[1], KEYS[4])
end
return rv
'''

    @retried
    async def _new_session_id(self):
        rv = self._session_id[:32] + hashlib.shake_128(
            os.urandom(16)).hexdigest(16)
        selector, validator = self._split(rv)
        new_nonce = self._make_nonce()
        to_del = self._get_del()
        ts = self._get_deadline()
        # noinspection PyUnresolvedReferences
        await self._update_with_new_validator(
            [
                selector,
                validator,
                str(ts).encode('utf-8'),
                int(ts * 1000),
                len(to_del),
                self._nonce,
            ],
            to_del + self._encode({NONCE: new_nonce}))
        self._nonce = new_nonce
        self._to_del.clear()
        self._values_changed.clear()
        self._cookie_deadline = ts
        return rv

    @script
    def _do_save(self):
        return f'''\
local rv
if (redis.call('HGET', KEYS[1], {NONCE_REPR}) ~= KEYS[2])
then
    rv = {{err = '{ConcurrentUpdateError.MATCH_REPLY}'}}
else
    rv = redis.call('HMSET', KEYS[1], unpack(ARGV, KEYS[3] + 1))
    if (KEYS[3] ~= '0')
    then
        redis.call('HDEL', KEYS[1], unpack(ARGV, 1, KEYS[3]))
    end
end
return rv
'''

    async def _save(self):
        selector, validator = self._split(self._session_id)
        new_nonce = self._make_nonce()
        to_del = self._get_del()
        # noinspection PyUnresolvedReferences
        await self._do_save(
            [
                selector,
                self._nonce,
                len(to_del),
            ],
            to_del + self._encode({NONCE: new_nonce}))
        self._nonce = new_nonce
        self._to_del.clear()
        self._values_changed.clear()

    @script
    def _do_destroy(self):
        return f'''\
local rv
if (redis.call('HGET', KEYS[1], {NONCE_REPR}) ~= KEYS[2])
then
    rv = {{err = '{ConcurrentUpdateError.MATCH_REPLY}'}}
else
    rv = redis.call('DEL', KEYS[1])
end
return rv
'''

    async def _destroy(self):
        selector, validator = self._split(self._session_id)
        # noinspection PyUnresolvedReferences
        await self._do_destroy([selector, self._nonce])
