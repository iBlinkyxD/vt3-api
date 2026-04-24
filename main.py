import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text
from database import engine, Base
from routes import auth, users, company, admin, funding_items, submissions, opp_cost, payments
import models.sponsorship       # noqa: F401 — ensures Sponsorship table is created by create_all
import models.submission        # noqa: F401 — ensures Submission table is created by create_all
import models.opp_cost_investor # noqa: F401 — ensures OppCostInvestor table is created by create_all
import models.preset_item       # noqa: F401 — ensures PresetItem table is created by create_all

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

# Lightweight column migrations — safe to run on every startup (IF NOT EXISTS)
with engine.connect() as _conn:
    _conn.execute(text(
        "ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS opp_cost_email_frequency VARCHAR DEFAULT 'monthly'"
    ))
    # Stripe billing columns
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR UNIQUE"))
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR"))
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status VARCHAR DEFAULT 'inactive'"))
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_id VARCHAR"))
    # Email change columns
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS pending_email VARCHAR"))
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_change_token VARCHAR"))
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_change_expires TIMESTAMP"))
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_change_cancel_token VARCHAR"))
    # Session versioning for post-change session invalidation
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS session_version INTEGER DEFAULT 1"))
    # Google linked flag
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_linked BOOLEAN DEFAULT FALSE"))
    # Stripe Connect Express account
    _conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_connect_id VARCHAR UNIQUE"))
    _conn.commit()

# Seed preset items on first startup
from routes.admin import seed_preset_items
from database import SessionLocal as _SessionLocal
with _SessionLocal() as _db:
    seed_preset_items(_db)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(company.router)
app.include_router(admin.router)
app.include_router(funding_items.router)
app.include_router(submissions.router)
app.include_router(opp_cost.router)
app.include_router(payments.router)