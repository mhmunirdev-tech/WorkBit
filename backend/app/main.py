from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.auth import router as auth_router
from app.api.banners import router as banners_router
from app.api.dashboard import router as dashboard_router
from app.api.offers import router as offers_router
from app.api.postbacks import router as postbacks_router
from app.api.profile import router as profile_router
from app.api.ranks import router as ranks_router
from app.api.wallet import router as wallet_router
from app.api.withdrawals import router as withdrawals_router
from app.core.config import settings
from app.core.errors import http_exception_handler, unexpected_exception_handler, validation_exception_handler
from app.core.logging import configure_logging

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

configure_logging()
app = FastAPI(title="WorkBit API", version="0.1.0", docs_url="/docs", openapi_url="/api/v1/openapi.json")
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-CSRF-Token"])
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unexpected_exception_handler)
from fastapi.exceptions import RequestValidationError
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(banners_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(offers_router, prefix="/api/v1")
app.include_router(postbacks_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(ranks_router, prefix="/api/v1")
app.include_router(wallet_router, prefix="/api/v1")
app.include_router(withdrawals_router, prefix="/api/v1")
@app.get("/health", tags=["system"])
def health() -> dict[str, str]: return {"status": "ok"}
