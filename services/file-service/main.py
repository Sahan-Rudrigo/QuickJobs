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
    print("File Service ready on port 8002")
    print("API docs: http://localhost:8002/docs")
    yield
    print("File Service shutting down...")


app = FastAPI(
    title="QuickJobs File Service",
    description="""
    Handles CV uploads from the WhatsApp Gateway.

    - Extracts text from PDF (digital + OCR) and DOCX files
    - Stores files in S3 with versioning (max 3 per user)
    - Publishes cv.uploaded events to SQS for the Matching Service
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
    return {"status": "ok", "service": "file-service", "port": 8002}


@app.get("/")
def root():
    return {"service": "QuickJobs File Service", "docs": "http://localhost:8002/docs"}
