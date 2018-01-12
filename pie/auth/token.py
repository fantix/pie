from sanic import response

from .api import bp
from .models import User, Token
from ..session.redis import Session

_actions = {}


def action(m):
    _actions[m.__name__] = m
    return m


@action
async def login(request, token: Token):
    conditions = []
    if token.email:
        conditions.append(User.email == token.email)
    if not conditions:
        return response.json(dict(success=False))
    u = await User.query.where(*conditions).execute().first()
    if u:
        session = await Session.of(request)
        session.set('uid', u.id)
    else:
        pass
    return response.text(token.email)


@bp.get('/token/<token:[a-fA-F0-9]{64}>')
async def token_login(request, token):
    async with request.app.engine.begin():
        token = await Token.verify(token.lower())
        if token is None:
            return response.text('invalid')
        else:
            await token.use()
            return await _actions[token.action](request, token)
