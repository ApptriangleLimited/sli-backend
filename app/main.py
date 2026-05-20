from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin_routes, agent_proposal_routes, auth_routes, underwriter_proposal_routes
from app.core.config import settings
from app.core.database import SessionLocal, create_missing_tables_and_columns
from app.seeders.default_admin import seed_default_admin
from app.seeders.default_roles import seed_default_roles
from app.seeders.default_underwriter import seed_default_underwriter
from app.utils.response import error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_missing_tables_and_columns()
    db = SessionLocal()
    try:
        seed_default_roles(db)
        seed_default_admin(db)
        seed_default_underwriter(db)
    finally:
        db.close()
    yield


app = FastAPI(title="SLI Backend API", version="1.0.0", lifespan=lifespan)

_cors_kwargs: dict = {
    "allow_origins": settings.cors_origin_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.cors_origin_regex:
    _cors_kwargs["allow_origin_regex"] = settings.cors_origin_regex

app.add_middleware(CORSMiddleware, **_cors_kwargs)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return error_response(message=str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(message="Validation failed", errors=exc.errors(), status_code=422)


@app.get("/health")
def health_check():
    return {"success": True, "message": "SLI backend is running", "data": None, "errors": None}


app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(agent_proposal_routes.router)
app.include_router(underwriter_proposal_routes.router)
