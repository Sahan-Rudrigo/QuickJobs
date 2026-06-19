from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from database import engine, Base
from routes import router
from redis_client import ping as redis_ping

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Creates all database tables automatically on first run.
    """
    print("Starting User Service...")

    # Create all tables in PostgreSQL if they don't exist
    # This runs automatically — no need to manually create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified")

    # Check Redis connection
    if redis_ping():
        print("Redis connection OK")
    else:
        print("WARNING: Redis connection failed. Opt-in caching will not work.")

    print("User Service ready on port 8001")
    print("API docs available at: http://localhost:8001/docs")

    yield

    print("User Service shutting down...")


app = FastAPI(
    title="QuickJobs User Service",
    description="""
    Manages job seeker profiles for the QuickJobs platform.

    This service handles:
    - Creating user profiles during WhatsApp onboarding
    - Storing all profile data (name, skills, experience, location, salary)
    - Updating profiles when users change info via WhatsApp menu
    - Managing opt-in/opt-out status for job alert notifications
    - PDPA compliance through user data deletion
    """,
    version="1.0.0",
    lifespan=lifespan
)

# Allow requests from frontend (Next.js dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production restrict to your Vercel URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all user routes
app.include_router(router)


@app.get("/health")
def health_check():
    """
    Health check endpoint.
    Used by teammates and monitoring to verify service is running.
    Also checks Redis and database connections.
    """
    redis_ok = redis_ping()
    return {
        "status": "ok",
        "service": "user-service",
        "port": 8001,
        "redis": "connected" if redis_ok else "disconnected",
        "database": "connected"
    }


@app.get("/")
def root():
    return {
        "service": "QuickJobs User Service",
        "version": "1.0.0",
        "docs": "http://localhost:8001/docs",
        "health": "http://localhost:8001/health"
    }
