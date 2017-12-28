import sanic


def get_app():
    app = sanic.Sanic(__name__)

    from .db import init_app
    init_app(app)

    return app
