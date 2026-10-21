"""Main FastAPI application entry point with CORS and routers."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.db.init_db import init_db
from backend.app.routers import auth, orgs, members

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables are initialized on startup."""
    init_db()
    yield

app = FastAPI(
    title="OrgLearn API",
    description="Multi-tenant Learning Platform with Role-Based Access Control (RBAC)",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(members.router)


@app.get("/health", tags=["system"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "product": "OrgLearn"}
