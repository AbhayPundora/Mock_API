import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.routers import organizations, people
from src.database.core import engine, SessionLocal, limiter
from src.models.models import Base, Organization

logger = logging.getLogger(__name__)

# rate limiter defined in database/core.py — imported here to attach to app


def _auto_seed():
    """Seed the DB on startup if it's empty. Safe to call multiple times."""
    db = SessionLocal()
    try:
        count = db.query(Organization).count()
        if count == 0:
            logger.info("Database is empty — running seed...")
            from src.seed import seed
            seed()
            logger.info("Seed complete.")
        else:
            logger.info(f"Database already has {count} organizations — skipping seed.")
    except Exception as e:
        logger.error(f"Seed failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        _auto_seed()
    except Exception as e:
        logger.error(f"Startup DB init failed: {e} — app will start anyway")
    yield


app = FastAPI(
    title="Apollo Mock API",
    description="Dummy Apollo API — mirrors real Apollo endpoints, data served from PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)

# attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(organizations.router)
app.include_router(people.router)


@app.get("/health")
def health():
    return {"status": "ok"}
