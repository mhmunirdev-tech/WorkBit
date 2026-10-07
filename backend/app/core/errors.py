import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

def error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"success": False, "error": {"code": code, "message": message}})

async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    messages = {
        401: ("UNAUTHENTICATED", "Authentication is required."),
        403: ("FORBIDDEN", "You do not have permission to perform this action."),
        404: ("NOT_FOUND", "The requested resource was not found."),
        503: ("SERVICE_UNAVAILABLE", "The service is temporarily unavailable."),
    }
    code, default = messages.get(exc.status_code, ("REQUEST_ERROR", "The request could not be completed."))
    message = str(exc.detail) if exc.status_code in {400, 503} else default
    return error(code, message, exc.status_code)


async def validation_exception_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return error("VALIDATION_ERROR", "Invalid request.", 422)


async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.error(
        "unhandled API exception method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return error("INTERNAL_SERVER_ERROR", "An unexpected error occurred.", 500)
