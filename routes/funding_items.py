from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.funding_item import FundingItem
from models.sponsorship import Sponsorship
from schemas.funding_item import FundingItemCreate, FundingItemUpdate, FundingItemOut
from schemas.sponsorship import SponsorshipCreate, SponsorshipOut
from utils.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/items", tags=["funding-items"])


@router.get("/public/{public_id}", response_model=List[FundingItemOut])
def get_public_items(public_id: str, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.public_id == public_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")
    return db.query(FundingItem).filter(FundingItem.owner_id == owner.id).all()


@router.get("/public/{public_id}/sponsors", response_model=List[SponsorshipOut])
def get_public_sponsors(public_id: str, limit: int = 20, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.public_id == public_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")

    item_ids = [
        row.id for row in db.query(FundingItem.id)
        .filter(FundingItem.owner_id == owner.id)
        .all()
    ]
    if not item_ids:
        return []

    rows = (
        db.query(Sponsorship)
        .filter(Sponsorship.item_id.in_(item_ids))
        .order_by(Sponsorship.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for s in rows:
        result.append(SponsorshipOut(
            id=s.id,
            item_id=s.item_id,
            display_name=s.display_name,
            units_funded=s.units_funded,
            amount_usd=s.amount_usd,
            created_at=s.created_at,
            item_title=s.item.title if s.item else "Unknown item",
            avatar_url=s.user.avatar_url if s.user else None,
        ))
    return result


@router.post("/public/{item_id}/sponsor", response_model=SponsorshipOut)
def sponsor_item(
    item_id: int,
    data: SponsorshipCreate,
    db: Session = Depends(get_db),
):
    item = db.query(FundingItem).filter(FundingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    units = min(data.units, item.units_needed - item.units_funded)
    if units <= 0:
        raise HTTPException(status_code=400, detail="Item is already fully funded")

    item.units_funded += units
    db.flush()

    sponsorship = Sponsorship(
        item_id=item.id,
        display_name=data.display_name,
        units_funded=units,
        amount_usd=units * item.price_per_unit,
    )
    db.add(sponsorship)
    db.commit()
    db.refresh(sponsorship)

    return SponsorshipOut(
        id=sponsorship.id,
        item_id=sponsorship.item_id,
        display_name=sponsorship.display_name,
        units_funded=sponsorship.units_funded,
        amount_usd=sponsorship.amount_usd,
        created_at=sponsorship.created_at,
        item_title=item.title,
    )


@router.get("", response_model=List[FundingItemOut])
def get_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(FundingItem).filter(FundingItem.owner_id == current_user.id).all()


@router.post("", response_model=FundingItemOut)
def create_item(
    data: FundingItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = FundingItem(**data.model_dump(), owner_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=FundingItemOut)
def update_item(
    item_id: int,
    data: FundingItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(FundingItem).filter(
        FundingItem.id == item_id,
        FundingItem.owner_id == current_user.id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(FundingItem).filter(
        FundingItem.id == item_id,
        FundingItem.owner_id == current_user.id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.query(Sponsorship).filter(Sponsorship.item_id == item_id).delete()
    db.delete(item)
    db.commit()
    return {"message": "Item deleted"}
