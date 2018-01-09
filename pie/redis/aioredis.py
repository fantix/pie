import aioredis
import sanic


def init_app(app: sanic.Sanic, *,
             parser=None, pool_cls=None, connection_cls=None):
    @app.listener('before_server_start')
    async def before_server_start(_, loop):
        assert not hasattr(app, 'redis')
        app.redis = await aioredis.create_redis_pool(
            app.config.get('REDIS_URI') or
            (app.config.get('REDIS_HOST', '127.0.0.1'),
             app.config.get('REDIS_PORT', 6379)),
            db=app.config.get('REDIS_DB'),
            password=app.config.get('REDIS_PASSWORD'),
            ssl=app.config.get('REDIS_SSL'),
            encoding=app.config.get('REDIS_ENCODING'),
            minsize=app.config.get('REDIS_MINSIZE', 1),
            maxsize=app.config.get('REDIS_MAXSIZE', 10),
            parser=parser,
            timeout=app.config.get('REDIS_CONNECT_TIMEOUT'),
            pool_cls=pool_cls,
            connection_cls=connection_cls,
            loop=loop,
            )

    @app.listener('after_server_stop')
    async def after_server_stop(*_):
        redis = getattr(app, 'redis', None)
        if redis is not None:
            redis.close()
            await redis.wait_closed()
