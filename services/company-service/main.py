from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from database import engine, Base
from routes import router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("Company Service ready on port 8003")
    print("API docs: http://localhost:8003/docs")
    yield
    print("Company Service shutting down...")


app = FastAPI(
    title="QuickJobs Company Service",
    description="""
    Manages employer companies and job listings.

    - Company registration and admin approval workflow
    - Job posting with automatic AI candidate matching
    - SQS event publishing for WhatsApp notifications
    """,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "company-service", "port": 8003}


@app.get("/")
def root():
    return {"service": "QuickJobs Company Service", "docs": "http://localhost:8003/docs"}
