import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routes import auth, users, company, admin, funding_items, submissions
import models.sponsorship  # noqa: F401 — ensures Sponsorship table is created by create_all
import models.submission   # noqa: F401 — ensures Submission table is created by create_all

app = FastAPI()

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://vt3.ai",
    "https://www.vt3.ai",
    "https://app.vt3.ai",
    "https://dev.vt3.ai",
    "https://dev-app.vt3.ai",
]

# Allow any extra origins injected via environment variable (comma-separated)
extra = os.getenv("EXTRA_CORS_ORIGINS", "")
if extra:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables in PostgreSQL
Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(company.router)
app.include_router(admin.router)
app.include_router(funding_items.router)
app.include_router(submissions.router)