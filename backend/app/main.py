"""
HealthBridge AI - Main FastAPI Application
AI-Driven Health Understanding & Assistance Platform
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.database.connection import init_db
from backend.app.safety.disclaimer import GLOBAL_DISCLAIMER_EN
from backend.app.api.auth import router as auth_router
from backend.app.api.symptoms import router as symptoms_router
from backend.app.api.diseases import router as diseases_router
from backend.app.api.medical_terms import router as terms_router
from backend.app.api.lab_tests import router as lab_router
from backend.app.api.evaluation import router as eval_router
from backend.app.api.search import router as search_router
from backend.app.api.reports import router as reports_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and seed knowledge on startup
    init_db()
    yield

app = FastAPI(
    title="HealthBridge AI",
    description="AI-Driven Health Understanding & Assistance Platform. Educational healthcare information and health-literacy platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for browser integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router)
app.include_router(symptoms_router)
app.include_router(diseases_router)
app.include_router(terms_router)
app.include_router(lab_router)
app.include_router(eval_router)
app.include_router(search_router)
app.include_router(reports_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "HealthBridge AI",
        "version": "1.0.0",
        "disclaimer": GLOBAL_DISCLAIMER_EN
    }

# Mount static frontend directory
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
