import sanic

bp = sanic.Blueprint('auth', url_prefix='auth')


def init_app(app: sanic.Sanic):
    from . import email
    from . import token

    app.blueprint(bp)
