"""
FastAPI application entry point for SecurePayAI.

Startup: Initialize database tables
Shutdown: Flush pending Kafka messages, close producer

Run with: uvicorn app.main:app --reload

Remember: this alone does nothing useful. You also need
`python -m app.kafka_consumer` running in a second terminal -
that's the process that actually scores transactions.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.kafka_producer import close_producer
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # startup
    init_db()
    yield
    # shutdown: flush pending Kafka messages, then close the producer
    close_producer()


app = FastAPI(title="SecurePayAI", version="0.1.0", lifespan=lifespan)

# DEV ONLY: lets a browser page on another origin call the API.
# In production, replace "*" with your real frontend origin(s).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "SecurePayAI Fraud Detection API", "version": "0.1.0"}
