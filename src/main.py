import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import organizations, people
from src.database.core import engine, SessionLocal
from src.models.models import Base, Organization

logger = logging.getLogger(__name__)


def _auto_seed():
    """Seed the DB on startup if it's empty. Safe to call multiple times."""
    db = SessionLocal()
    try:
        count = db.query(Organization).count()
        if count == 0:
            logger.info("Database is empty — running seed...")
            # import here to avoid circular imports at module load time
            from src.seed import seed
            seed()
            logger.info("Seed complete.")
        else:
            logger.info(f"Database already has {count} organizations — skipping seed.")
    except Exception as e:
        logger.error(f"Seed failed: {e}")
        raise
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create tables then seed on startup
    Base.metadata.create_all(bind=engine)
    _auto_seed()
    yield


app = FastAPI(
    title="Apollo Mock API",
    description="Dummy Apollo API — mirrors real Apollo endpoints, data served from PostgreSQL.",
    version="1.0.0",
    lifespan=lifespan,
)

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
