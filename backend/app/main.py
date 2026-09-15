from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.routers import sync, timesheets
from app.services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(title="Jira Timesheets API", lifespan=lifespan)


@app.middleware("http")
async def secure_api_responses(request: Request, call_next):
    # The application has no browser session or application-level authentication,
    # so its primary boundary remains the private network/reverse proxy. Requiring
    # JSON for state-changing requests additionally prevents a public webpage from
    # reaching a user's internal API with a simple cross-origin HTML form POST.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        content_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
        if content_type != "application/json":
            response = JSONResponse(
                status_code=415,
                content={"detail": "State-changing requests require application/json"},
            )
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)

app.include_router(timesheets.router)
app.include_router(sync.router)
