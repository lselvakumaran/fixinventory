import logging

from aiohttp.web import Request, HTTPRedirection, StreamResponse, HTTPNotFound, HTTPBadRequest, HTTPException
from aiohttp.web_middlewares import middleware

from core.error import NotFoundError
from core.metrics import RequestInProgress, RequestLatency, RequestCount, perf_now
from core.web import RequestHandler

log = logging.getLogger(__name__)


@middleware
async def metrics_handler(request: Request, handler: RequestHandler) -> StreamResponse:
    request["start_time"] = perf_now()
    RequestInProgress.labels(request.path, request.method).inc()
    try:
        response = await handler(request)
        RequestCount.labels(request.method, request.path, response.status).inc()
        return response
    except HTTPException as ex:
        RequestCount.labels(request.method, request.path, ex.status).inc()
        raise ex
    finally:
        resp_time = perf_now() - request["start_time"]
        RequestLatency.labels(request.path).observe(resp_time)
        RequestInProgress.labels(request.path, request.method).dec()


@middleware
async def error_handler(request: Request, handler: RequestHandler) -> StreamResponse:
    try:
        response = await handler(request)
        return response
    except HTTPRedirection as e:
        # redirects are implemented as exceptions in aiohttp for whatever reason...
        raise e
    except NotFoundError as e:
        kind = type(e).__name__
        message = f"Error: {kind}\nMessage: {str(e)}"
        log.info(f"Request {request} has failed with exception: {message}", exc_info=e)
        raise HTTPNotFound(text=message) from e
    except Exception as e:
        kind = type(e).__name__
        message = f"Error: {kind}\nMessage: {str(e)}"
        log.warning(f"Request {request} has failed with exception: {message}", exc_info=e)
        raise HTTPBadRequest(text=message) from e
