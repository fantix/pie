import time

import sanic
from sanic.request import Request
from sanic.response import BaseHTTPResponse

_no_default = object()


class Session:
    key = 'pie.session.base.Session'
    cookie_name = 'PIE_SESSION_BASE_SESSION'
    ttl = 1024
    refresh_threshold = 128
    refresh_wait = 4

    def __init__(self, request: Request, using_cookie=False):
        self._request = request
        self._app = request.app
        self._loaded = None
        self._session_id = None
        self._values = None
        self._values_changed = set()
        self._to_del = set()
        self._using_cookie = using_cookie
        self._cookie_deadline = None
        self._should_refresh = False

    # noinspection PyMethodMayBeStatic
    def _sanitize_session_id(self, session_id: str) -> str:
        if not session_id or len(session_id) != 64:
            return None
        session_id = session_id.lower()
        for char in session_id:
            if char not in '1234567890abcdef':
                return None
        return session_id

    def _get_session_id(self):
        rv = self._request.cookies.get(self.cookie_name)
        if rv:
            self._using_cookie = True
        else:
            rv = self._request.token
        return rv

    async def _load(self) -> dict:
        pass

    async def _new_session(self) -> str:
        pass

    async def _new_session_id(self) -> str:
        pass

    async def _save(self):
        pass

    async def _destroy(self):
        pass

    async def load(self):
        if self._loaded is None:
            self._loaded = self._request.app.loop.create_future()
            try:
                self._session_id = self._sanitize_session_id(
                    self._get_session_id())
                if self._session_id:
                    self._values = await self._load()
                    if self._values is None:
                        self._cookie_deadline = 1
                        self._values = {}
                        self._session_id = None
                else:
                    self._cookie_deadline = 1
                    self._values = {}
                self._loaded.set_result(None)
            except BaseException as e:
                self._loaded.set_exception(e)
                raise
        else:
            await self._loaded
        return self

    async def save(self, refresh=False):
        if not self._loaded:
            return
        await self._loaded
        if self._should_refresh:
            refresh = True
        if not (refresh or self._values_changed or self._to_del):
            return
        rv = None
        if self._session_id:
            if refresh:
                rv = self._session_id = await self._new_session_id()
                self._should_refresh = False
            else:
                await self._save()
        else:
            rv = self._session_id = await self._new_session()
        return rv

    async def destroy(self):
        await self.load()
        if self._session_id:
            await self._destroy()
            self._session_id = None
            self._values = None
            self._values_changed.clear()
            self._to_del.clear()
        self._cookie_deadline = 1

    def set_cookie(self, response: BaseHTTPResponse):
        if not self._cookie_deadline:
            return

        if self._session_id:
            secure = False
            domain = None
            path = '/'

            response.cookies[self.cookie_name] = self._session_id

            expires = self._cookie_deadline
            expiry = max(0, expires - time.time())
            expires = time.strftime("%a, %d-%b-%Y %T GMT",
                                    time.gmtime(expires))
            response.cookies[self.cookie_name]['expires'] = expires
            response.cookies[self.cookie_name]['max-age'] = expiry
            response.cookies[self.cookie_name]['httponly'] = True
            response.cookies[self.cookie_name]['secure'] = secure
            response.cookies[self.cookie_name]['path'] = path

            if domain:
                response.cookies[self.cookie_name]['domain'] = domain
        else:
            del response.cookies[self.cookie_name]
        self._cookie_deadline = 0

    def get(self, key, default=None):
        assert self._loaded, 'Please load the session first.'
        return self._values.get(key, default)

    def set(self, key, value):
        assert self._loaded, 'Please load the session first.'
        self._values[key] = value
        self._values_changed.add(key)
        self._to_del.discard(key)

    def pop(self, key, default=_no_default):
        assert self._loaded, 'Please load the session first.'
        if default is _no_default:
            rv = self._values.pop(key)
        else:
            rv = self._values.pop(key, default)
        self._to_del.add(key)
        self._values_changed.discard(key)
        return rv

    async def on_response(self, response: BaseHTTPResponse):
        await self.save()
        if self._using_cookie:
            self.set_cookie(response)

    @classmethod
    def install(cls, app: sanic.Sanic):
        @app.middleware('response')
        async def on_response(request, response):
            session = cls.of(request, create=False)  # type: cls
            if session is not None:
                await session.on_response(response)

    @classmethod
    def of(cls, request: Request, using_cookie=False, create=True):
        rv = request.get(cls.key)
        if rv is None:
            if create:
                rv = cls(request, using_cookie)
                request[cls.key] = rv
        elif using_cookie:
            rv._using_cookie = True
        return rv

    def __init_subclass__(cls, **kwargs):
        cls.key = f'{cls.__module__}'
        cls.cookie_name = cls.key.replace('.', '_').upper()

    def __await__(self):
        return self.load().__await__()

    async def __aenter__(self):
        await self.load()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            await self.save()
        else:
            self._request.pop(self.key, None)
