import functools

import sanic
from sanic.request import Request
from sanic.response import text

from ..session.redis import Session


class Login:
    pass


def load_identity(m):
    @functools.wraps(m)
    async def wrapper(request, *args, **kwargs):

        pass
    return wrapper


def init_app(app: sanic.Sanic):
    @app.route('/')
    async def test(request: Request):
        session = await Session.of(request)
        return text(str(session.get('data')))

    @app.route('/login')
    async def login(request: Request):
        session = await Session.of(request, True)
        if session.get('data'):
            await session.save(refresh=True)
            return text('already in')
        else:
            session.set('data', 'logged in')
            return text('success')

    @app.route('/logout')
    async def login(request: Request):
        session = await Session.of(request)
        if session.get('data'):
            await session.destroy()
            # session.pop('data')
            return text('success')
        else:
            return text('already out')
