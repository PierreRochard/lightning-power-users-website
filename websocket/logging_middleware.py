from aiohttp import web

from website.logger import log


@web.middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
        return response
    except Exception:
        log.error('Exception', exc_info=True)
        raise
