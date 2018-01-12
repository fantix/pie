import functools


def retry_on(error: type, *, times=2):
    def decorator(m):
        @functools.wraps(m)
        async def wrapper(*args, **kwargs):
            for count in range(times):
                try:
                    return await m(*args, **kwargs)
                except error:
                    if count == times - 1:
                        raise
        return wrapper
    return decorator
