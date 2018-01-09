import sanic


def get_app():
    app = sanic.Sanic(__name__)

    from .db import init_app
    init_app(app)

    from .redis.aioredis import init_app
    init_app(app)

    from .session.redis import Session
    Session.install(app)

    from .auth.login import init_app
    init_app(app)

    return app
