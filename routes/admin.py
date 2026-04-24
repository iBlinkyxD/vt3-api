import os
import httpx

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.user import User
from models.preset_item import PresetItem
from schemas.user import UserStatusUpdate
from schemas.preset_item import PresetItemCreate, PresetItemUpdate, PresetItemOut
from utils.auth import admin_required

router = APIRouter(prefix="/admin", tags=["admin"])

SUPABASE_URL       = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
ICON_BUCKET        = "preset-icons"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}


# ── Seed data (mirrors packages/shared/src/data/item.ts) ─────────────────────
SEED_ITEMS = [
    {"name": "OpenAI API",        "category": "AI & Machine Learning",  "description": "LLM APIs for chatbots, embeddings, and AI apps",          "pricing_plans": [{"id":"starter","name":"Starter Credits","price":50,"duration":"month","features":["GPT models access","API usage credits","Embeddings"]},{"id":"growth","name":"Growth Credits","price":500,"duration":"month","features":["Higher rate limits","Priority API access","Advanced models"]}]},
    {"name": "Hugging Face",       "category": "AI & Machine Learning",  "description": "Model hosting, inference endpoints and datasets",          "pricing_plans": [{"id":"pro","name":"Pro","price":9,"duration":"month","features":["Private models","Inference endpoints","Priority GPU access"]},{"id":"enterprise","name":"Enterprise","price":50,"duration":"month","features":["Team collaboration","Dedicated resources","Enterprise support"]}]},
    {"name": "Replicate",          "category": "AI & Machine Learning",  "description": "Run open-source AI models in the cloud",                  "pricing_plans": [{"id":"payg","name":"Pay as you go","price":30,"duration":"month","features":["Model hosting","GPU inference","API access"]}]},
    {"name": "AWS",                "category": "Cloud & Hosting",        "description": "Scalable cloud infrastructure and services",               "pricing_plans": [{"id":"startup","name":"Startup Credits","price":100,"duration":"month","features":["EC2 compute","S3 storage","Cloud deployment"]},{"id":"scale","name":"Scaling Infra","price":1000,"duration":"month","features":["High availability infra","Load balancing","Managed services"]}]},
    {"name": "Vercel",             "category": "Cloud & Hosting",        "description": "Frontend cloud for modern web applications",               "pricing_plans": [{"id":"pro","name":"Pro","price":20,"duration":"month","features":["Serverless functions","Edge network","Analytics"]}]},
    {"name": "Cloudflare",         "category": "Cloud & Hosting",        "description": "CDN, DNS, and security infrastructure",                    "pricing_plans": [{"id":"pro","name":"Pro","price":20,"duration":"month","features":["Global CDN","DDoS protection","Advanced caching"]}]},
    {"name": "GitHub",             "category": "Developer Tools",        "description": "Code hosting and collaboration platform",                  "pricing_plans": [{"id":"team","name":"Team","price":4,"duration":"month","features":["Unlimited repos","Protected branches","Team access"]},{"id":"enterprise","name":"Enterprise","price":21,"duration":"month","features":["Advanced security","Audit logs","Priority support"]}]},
    {"name": "Docker",             "category": "Developer Tools",        "description": "Container platform for building and shipping apps",        "pricing_plans": [{"id":"pro","name":"Pro","price":5,"duration":"month","features":["Private repos","Advanced builds","Team collaboration"]}]},
    {"name": "JetBrains IDEs",     "category": "Developer Tools",        "description": "Professional development environments",                    "pricing_plans": [{"id":"all-products","name":"All Products Pack","price":29,"duration":"month","features":["All IDEs","Code analysis","Developer tools"]}]},
    {"name": "Supabase",           "category": "Data & Databases",       "description": "Open-source backend with PostgreSQL database",             "pricing_plans": [{"id":"pro","name":"Pro","price":25,"duration":"month","features":["Managed PostgreSQL","Auth","Storage"]}]},
    {"name": "MongoDB Atlas",      "category": "Data & Databases",       "description": "Cloud-hosted NoSQL database",                             "pricing_plans": [{"id":"shared","name":"Shared Cluster","price":9,"duration":"month","features":["Managed cluster","Scalable storage","Security"]}]},
    {"name": "Snowflake",          "category": "Data & Databases",       "description": "Enterprise data warehouse",                               "pricing_plans": [{"id":"standard","name":"Standard","price":40,"duration":"month","features":["Data warehousing","Analytics engine","Secure sharing"]}]},
    {"name": "Figma",              "category": "Design & Product",       "description": "Collaborative interface design tool",                      "pricing_plans": [{"id":"professional","name":"Professional","price":15,"duration":"month","features":["Unlimited files","Version history","Team libraries"]}]},
    {"name": "Framer",             "category": "Design & Product",       "description": "Interactive design and website builder",                   "pricing_plans": [{"id":"mini","name":"Mini","price":10,"duration":"month","features":["Landing pages","Custom domains","Analytics"]}]},
    {"name": "Canva",              "category": "Design & Product",       "description": "Graphic design platform for marketing assets",             "pricing_plans": [{"id":"pro","name":"Pro","price":13,"duration":"month","features":["Premium assets","Brand kit","Content planner"]}]},
    {"name": "Notion",             "category": "Productivity Tools",     "description": "Workspace for documentation and collaboration",            "pricing_plans": [{"id":"plus","name":"Plus","price":10,"duration":"month","features":["Unlimited blocks","File uploads","Team collaboration"]}]},
    {"name": "Slack",              "category": "Productivity Tools",     "description": "Team messaging platform",                                 "pricing_plans": [{"id":"pro","name":"Pro","price":8,"duration":"month","features":["Unlimited message history","Group calls","App integrations"]}]},
    {"name": "Google Workspace",   "category": "Productivity Tools",     "description": "Email, docs, and collaboration tools",                    "pricing_plans": [{"id":"business","name":"Business Standard","price":12,"duration":"month","features":["Gmail","Drive storage","Docs and Meet"]}]},
    {"name": "Stripe",             "category": "Payments & Finance",     "description": "Payment processing and billing platform",                 "pricing_plans": [{"id":"standard","name":"Standard","price":0,"duration":"usage","features":["2.9% + 30¢ per transaction","Subscriptions","Global payments"]}]},
    {"name": "Intercom",           "category": "Customer Support",       "description": "Customer messaging and support platform",                 "pricing_plans": [{"id":"starter","name":"Starter","price":39,"duration":"month","features":["Live chat","Help center","Basic automation"]}]},
    {"name": "Datadog",            "category": "Security & DevOps",      "description": "Infrastructure monitoring and observability",              "pricing_plans": [{"id":"infra","name":"Infrastructure","price":15,"duration":"month","features":["Server monitoring","Metrics dashboard","Alerts"]}]},
    {"name": "MacBook Pro",        "category": "Hardware",               "description": "High performance laptop for developers",                  "pricing_plans": [{"id":"base","name":"Base Model","price":2499,"duration":"one-time","features":["M3 chip","16GB RAM","512GB SSD"]}]},
]


def seed_preset_items(db: Session):
    if db.query(PresetItem).count() == 0:
        for i, item in enumerate(SEED_ITEMS):
            db.add(PresetItem(
                name=item["name"],
                category=item["category"],
                description=item["description"],
                icon_url=None,
                pricing_plans=item["pricing_plans"],
                sort_order=i,
                is_active=True,
            ))
        db.commit()


# ── User management (existing) ────────────────────────────────────────────────

@router.get("/users")
def get_all_users(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    users = db.query(User).all()
    return users


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_verified is not None:
        user.is_verified = data.is_verified
    db.commit()
    db.refresh(user)
    return {"message": "User status updated", "user": {"id": user.id, "is_active": user.is_active, "is_verified": user.is_verified}}


# ── Preset items — public read ─────────────────────────────────────────────────

@router.get("/preset-items/public", response_model=List[PresetItemOut])
def get_public_preset_items(db: Session = Depends(get_db)):
    """Unauthenticated — used by AddItemModal to load preset tools."""
    return db.query(PresetItem).filter(PresetItem.is_active == True).order_by(PresetItem.sort_order).all()


# ── Preset items — admin CRUD ──────────────────────────────────────────────────

@router.get("/preset-items", response_model=List[PresetItemOut])
def get_preset_items(db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    return db.query(PresetItem).order_by(PresetItem.sort_order).all()


@router.post("/preset-items", response_model=PresetItemOut)
def create_preset_item(body: PresetItemCreate, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    item = PresetItem(**body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/preset-items/{item_id}", response_model=PresetItemOut)
def update_preset_item(item_id: int, body: PresetItemUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    item = db.query(PresetItem).filter(PresetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Preset item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/preset-items/{item_id}")
def delete_preset_item(item_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_required)):
    item = db.query(PresetItem).filter(PresetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Preset item not found")
    db.delete(item)
    db.commit()
    return {"message": "Deleted"}


# ── Icon upload ────────────────────────────────────────────────────────────────

@router.post("/preset-items/{item_id}/icon")
async def upload_preset_icon(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type. Use JPEG, PNG, WebP, or SVG.")

    item = db.query(PresetItem).filter(PresetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Preset item not found")

    ext = (file.filename or "icon").rsplit(".", 1)[-1].lower()
    path = f"{item_id}/icon.{ext}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{ICON_BUCKET}/{path}"

    file_data = await file.read()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            upload_url,
            content=file_data,
            headers={
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": file.content_type or "application/octet-stream",
                "x-upsert": "true",
            },
        )
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Supabase upload failed: {resp.text}")

    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{ICON_BUCKET}/{path}"
    item.icon_url = public_url
    db.commit()

    return {"icon_url": public_url}
