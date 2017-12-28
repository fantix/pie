import sanic
import sqlalchemy as sa
from gino import declarative_base

metadata = sa.MetaData()
Model = declarative_base(metadata)


def init_app(app: sanic.Sanic):
    from .auth import models

    # noinspection PyShadowingNames
    @app.listener('before_server_start')
    async def before_server_start(app: sanic.Sanic, loop):
        app.engine = await sa.create_engine(
            'asyncpg://localhost/pie', strategy='gino', loop=loop)

    # noinspection PyShadowingNames
    @app.listener('after_server_stop')
    async def after_server_stop(app, _):
        try:
            engine = getattr(app, 'engine')
            delattr(app, 'engine')
        except AttributeError:
            pass
        else:
            engine.dispose()
