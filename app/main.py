"""FastAPI entrypoint. `uvicorn app.main:app` starts the UI, scheduler, and bot."""

import base64
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.bot.runner import bot_runner
from app.config import EnvSettings, get_env, set_env
from app.db import init_db
from app.logging_config import configure_logging
from app.scheduler import start_scheduler, stop_scheduler
from app.web.routes import WEB_DIR, render_not_found, router


def create_app(env: EnvSettings | None = None) -> FastAPI:
    settings = env or EnvSettings()
    set_env(settings)
    configure_logging(settings.log_level)
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    init_db(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not app.state.env.disable_scheduler:
            start_scheduler()
        if not app.state.env.disable_bot:
            await bot_runner.sync()
        yield
        await bot_runner.stop()
        stop_scheduler()

    app = FastAPI(title="Rabbat-IQ", version=__version__, lifespan=lifespan)
    app.state.env = settings
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.middleware("http")(cross_origin_guard)
    app.middleware("http")(basic_auth)
    app.middleware("http")(security_headers)

    @app.get("/health")
    def health():
        return {"ok": True, "version": __version__}

    return app


async def _http_error(request, exc: StarletteHTTPException):
    if exc.status_code == 404 and request.url.path != "/health":
        accept = request.headers.get("accept", "")
        if "text/html" in accept or "*/*" in accept or not accept:
            return render_not_found(request)
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


def _content_security_policy(host: str) -> str:
    # Live design mode loads from localhost:8400. Only a loopback request gets that allowance.
    # Leaflet positions tiles and pins with style attributes, so style-src-attr allows that
    # without opening stylesheet injection. Street tiles come from OpenStreetMap France.
    live = ""
    if host.lower() in {"localhost", "127.0.0.1"}:
        live = " http://localhost:8400"
    connect = f"; connect-src 'self'{live}" if live else ""
    tiles = (
        "https://a.tile.openstreetmap.fr https://b.tile.openstreetmap.fr "
        "https://c.tile.openstreetmap.fr"
    )
    return (
        "default-src 'self'; "
        f"img-src 'self' https://cdn.marktguru.de https://cdn.marktguru.at {tiles} data:; "
        "style-src 'self'; style-src-attr 'unsafe-inline'; "
        f"script-src 'self'{live}{connect}; form-action 'self'; "
        "base-uri 'self'; frame-ancestors 'none'"
    )


async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = _content_security_policy(
        request.url.hostname or ""
    )
    return response


async def basic_auth(request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    env = get_env()
    if not env.basic_auth_user and not env.basic_auth_password:
        return await call_next(request)
    if _basic_ok(request.headers.get("authorization", ""), env.basic_auth_user, env.basic_auth_password):
        return await call_next(request)
    return Response(
        "Authentication required",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Rabbat-IQ"'},
    )


def _basic_ok(header: str, user: str, password: str) -> bool:
    if not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    username, _, supplied = decoded.partition(":")
    return secrets.compare_digest(username, user) and secrets.compare_digest(supplied, password)


async def cross_origin_guard(request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        if origin and host:
            allowed = {f"http://{host}", f"https://{host}"}
            if origin.rstrip("/") not in allowed:
                return PlainTextResponse("Cross-origin form posts are blocked.", status_code=403)
    return await call_next(request)


app = create_app()
