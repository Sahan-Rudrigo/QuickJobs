import threading
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from sqs_consumer import poll_job_matched_queue

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SQS_JOB_MATCHED_URL"):
        t = threading.Thread(target=poll_job_matched_queue, daemon=True)
        t.start()
        print("[INFO] SQS consumer thread started")
    else:
        print("[WARN] SQS_JOB_MATCHED_URL not set — consumer not started")
    yield


app = FastAPI(
    title="QuickJobs Notification Service",
    description="Consumes job-matched SQS events and sends WhatsApp alerts to candidates.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service", "port": 8005}


@app.get("/")
def root():
    return {"service": "QuickJobs Notification Service"}
