import sanic
from gino.ext.sanic import Gino

db = Gino()


def init_app(app: sanic.Sanic):
    from .auth import models

    app.config.setdefault('DB_DATABASE', 'pie')
    db.init_app(app)
