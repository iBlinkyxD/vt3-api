from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.opp_cost_investor import OppCostInvestor
from models.opportunity import Opportunity
from schemas.opp_cost import (
    OppCostInvestorCreate,
    OppCostInvestorOut,
    OppCostSettingsUpdate,
    OppCostSettingsOut,
)
from utils.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/opp-cost", tags=["opp-cost"])


def _get_or_create_opportunity(user: User, db: Session) -> Opportunity:
    if not user.company_id:
        raise HTTPException(status_code=400, detail="User has no company")
    opp = db.query(Opportunity).filter(Opportunity.company_id == user.company_id).first()
    if not opp:
        opp = Opportunity(
            company_id=user.company_id,
            current_valuation=0,
            opp_cost_email_frequency="monthly",
        )
        db.add(opp)
        db.commit()
        db.refresh(opp)
    return opp


@router.get("/settings", response_model=OppCostSettingsOut)
def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    opp = _get_or_create_opportunity(current_user, db)
    return OppCostSettingsOut(
        current_valuation=opp.current_valuation or 0,
        email_frequency=opp.opp_cost_email_frequency or "monthly",
    )


@router.put("/settings")
def update_settings(
    data: OppCostSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    opp = _get_or_create_opportunity(current_user, db)
    if data.current_valuation is not None:
        opp.current_valuation = data.current_valuation
    if data.email_frequency is not None:
        opp.opp_cost_email_frequency = data.email_frequency
    db.commit()
    return {"message": "Settings updated"}


@router.get("/investors", response_model=List[OppCostInvestorOut])
def get_investors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(OppCostInvestor)
        .filter(OppCostInvestor.user_id == current_user.id)
        .order_by(OppCostInvestor.created_at.desc())
        .all()
    )


@router.post("/investors", response_model=OppCostInvestorOut)
def create_investor(
    data: OppCostInvestorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    investor = OppCostInvestor(user_id=current_user.id, **data.model_dump())
    db.add(investor)
    db.commit()
    db.refresh(investor)
    return investor


@router.put("/investors/{investor_id}", response_model=OppCostInvestorOut)
def update_investor(
    investor_id: int,
    data: OppCostInvestorCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    investor = db.query(OppCostInvestor).filter(
        OppCostInvestor.id == investor_id,
        OppCostInvestor.user_id == current_user.id,
    ).first()
    if not investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    for key, value in data.model_dump().items():
        setattr(investor, key, value)
    db.commit()
    db.refresh(investor)
    return investor


@router.delete("/investors/{investor_id}")
def delete_investor(
    investor_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    investor = db.query(OppCostInvestor).filter(
        OppCostInvestor.id == investor_id,
        OppCostInvestor.user_id == current_user.id,
    ).first()
    if not investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    db.delete(investor)
    db.commit()
    return {"message": "Investor deleted"}
