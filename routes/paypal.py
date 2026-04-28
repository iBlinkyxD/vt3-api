from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.user import User
from models.funding_item import FundingItem
from models.sponsorship import Sponsorship
from utils.paypal import create_paypal_order, capture_paypal_order, send_payout

router = APIRouter(prefix="/paypal", tags=["paypal"])


class CreateOrderRequest(BaseModel):
    item_id: int
    quantity: int = 1
    founder_public_id: str
    return_url: str
    cancel_url: str


class CaptureOrderRequest(BaseModel):
    order_id: str
    item_id: int
    quantity: int = 1
    founder_public_id: str
    display_name: str = "Anonymous"
    user_id: Optional[int] = None


@router.post("/create-order")
async def paypal_create_order(body: CreateOrderRequest, db: Session = Depends(get_db)):
    founder = db.query(User).filter(
        User.public_id == body.founder_public_id,
        User.is_deleted == False,
    ).first()
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")
    if not founder.paypal_email:
        raise HTTPException(status_code=400, detail="Founder has not configured PayPal payouts")

    item = db.query(FundingItem).filter(FundingItem.id == body.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    total_usd = round(item.price_per_unit * max(1, body.quantity), 2)

    try:
        order_id, approve_url = await create_paypal_order(
            amount_usd=total_usd,
            item_title=item.title,
            return_url=body.return_url,
            cancel_url=body.cancel_url,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"order_id": order_id, "approve_url": approve_url}


@router.post("/capture-order")
async def paypal_capture_order(body: CaptureOrderRequest, db: Session = Depends(get_db)):
    founder = db.query(User).filter(
        User.public_id == body.founder_public_id,
        User.is_deleted == False,
    ).first()
    if not founder or not founder.paypal_email:
        raise HTTPException(status_code=404, detail="Founder not found or PayPal not configured")

    item = db.query(FundingItem).filter(FundingItem.id == body.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        result = await capture_paypal_order(body.order_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.get("status") != "COMPLETED":
        raise HTTPException(status_code=400, detail=f"Payment not completed: {result.get('status')}")

    quantity  = max(1, body.quantity)
    total_usd = round(item.price_per_unit * quantity, 2)

    item.units_funded = min(item.units_funded + quantity, item.units_needed)
    db.add(Sponsorship(
        item_id=item.id,
        user_id=body.user_id,
        display_name=body.display_name,
        units_funded=quantity,
        amount_usd=total_usd,
    ))
    db.commit()

    try:
        await send_payout(
            founder.paypal_email,
            total_usd,
            note=f"VT3 payout for '{item.title}' — {quantity} unit(s)",
        )
    except RuntimeError as e:
        print(f"[PayPal payout error] order={body.order_id}: {e}")

    return {"success": True}
