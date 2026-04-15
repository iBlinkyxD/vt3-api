import os
import stripe

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_user
from models.user import User
from schemas.payment import CheckoutSessionCreate, CheckoutSessionOut, BillingPortalOut

router = APIRouter(prefix="/payments", tags=["payments"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Map plan slug + billing period → Stripe Price ID
PRICE_IDS: dict[str, dict[str, str]] = {
    "light": {
        "monthly": os.getenv("STRIPE_PRICE_LIGHT_MONTHLY", ""),
        "yearly":  os.getenv("STRIPE_PRICE_LIGHT_YEARLY", ""),
    },
    "basic": {
        "monthly": os.getenv("STRIPE_PRICE_BASIC_MONTHLY", ""),
        "yearly":  os.getenv("STRIPE_PRICE_BASIC_YEARLY", ""),
    },
    "advanced": {
        "monthly": os.getenv("STRIPE_PRICE_ADVANCED_MONTHLY", ""),
        "yearly":  os.getenv("STRIPE_PRICE_ADVANCED_YEARLY", ""),
    },
}

SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "")
CANCEL_URL  = os.getenv("STRIPE_CANCEL_URL",  "")


@router.post("/create-checkout-session", response_model=CheckoutSessionOut)
def create_checkout_session(
    body: CheckoutSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan    = body.plan.lower()
    billing = body.billing.lower()

    price_id = PRICE_IDS.get(plan, {}).get(billing)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan/billing combo: {plan}/{billing}")

    # Get or create a Stripe Customer tied to this user
    if current_user.stripe_customer_id:
        customer_id = current_user.stripe_customer_id
    else:
        customer = stripe.Customer.create(
            email=current_user.email,
            name=f"{current_user.first_name or ''} {current_user.last_name or ''}".strip(),
            metadata={"user_id": str(current_user.id)},
        )
        customer_id = customer.id
        current_user.stripe_customer_id = customer_id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        metadata={
            "user_id": str(current_user.id),
            "plan": plan,
            "billing": billing,
        },
        subscription_data={
            "metadata": {
                "user_id": str(current_user.id),
                "plan": plan,
            }
        },
    )

    return {"url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload   = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    event_type = event["type"]
    data_obj   = event["data"]["object"].to_dict()

    # ── checkout.session.completed ──────────────────────────────────────────
    if event_type == "checkout.session.completed":
        user_id = data_obj.get("metadata", {}).get("user_id")
        plan    = data_obj.get("metadata", {}).get("plan")
        sub_id  = data_obj.get("subscription")

        if user_id:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                user.subscription_status = "active"
                user.subscription_plan   = plan
                user.subscription_id     = sub_id
                db.commit()

    # ── invoice.payment_succeeded ───────────────────────────────────────────
    elif event_type == "invoice.payment_succeeded":
        sub_id = data_obj.get("subscription")
        if sub_id:
            user = db.query(User).filter(User.subscription_id == sub_id).first()
            if user:
                user.subscription_status = "active"
                db.commit()

    # ── invoice.payment_failed ──────────────────────────────────────────────
    elif event_type == "invoice.payment_failed":
        sub_id = data_obj.get("subscription")
        if sub_id:
            user = db.query(User).filter(User.subscription_id == sub_id).first()
            if user:
                user.subscription_status = "past_due"
                db.commit()

    # ── customer.subscription.deleted ──────────────────────────────────────
    elif event_type == "customer.subscription.deleted":
        sub_id = data_obj.get("id")
        if sub_id:
            user = db.query(User).filter(User.subscription_id == sub_id).first()
            if user:
                user.subscription_status = "inactive"
                user.subscription_plan   = None
                user.subscription_id     = None
                db.commit()

    # ── customer.subscription.updated ──────────────────────────────────────
    elif event_type == "customer.subscription.updated":
        sub_id = data_obj.get("id")
        status = data_obj.get("status")           # 'active' | 'past_due' | 'canceled' | etc.
        plan   = data_obj.get("metadata", {}).get("plan")

        if sub_id:
            user = db.query(User).filter(User.subscription_id == sub_id).first()
            if user:
                if status:
                    user.subscription_status = status
                if plan:
                    user.subscription_plan = plan
                db.commit()

    return {"received": True}


@router.get("/sync")
def sync_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pull the latest subscription state from Stripe and persist it to the DB.
    Called client-side after a successful Stripe Checkout redirect."""
    customer_id = current_user.stripe_customer_id

    # If no customer ID on record, look up by email in Stripe
    if not customer_id:
        customers = stripe.Customer.list(email=current_user.email, limit=1)
        if customers.data:
            customer_id = customers.data[0].id
            current_user.stripe_customer_id = customer_id
            db.commit()

    if not customer_id:
        return {"status": "inactive"}

    # Find active subscription
    subscriptions = stripe.Subscription.list(
        customer=customer_id,
        status="active",
        limit=1,
    )

    if subscriptions.data:
        sub = subscriptions.data[0]

        # Try metadata first, then reverse-lookup from price ID
        try:
            plan = sub["metadata"]["plan"]
        except (KeyError, TypeError):
            plan = None

        if not plan:
            try:
                price_id = sub["items"]["data"][0]["price"]["id"]
                for slug, periods in PRICE_IDS.items():
                    if price_id in periods.values():
                        plan = slug
                        break
            except (KeyError, IndexError, TypeError):
                pass

        current_user.subscription_status = "active"
        current_user.subscription_plan = plan or current_user.subscription_plan
        current_user.subscription_id = sub.id
        db.commit()
    else:
        # Capture any non-active state (past_due, canceled, etc.)
        all_subs = stripe.Subscription.list(customer=customer_id, limit=1)
        if all_subs.data:
            sub = all_subs.data[0]
            current_user.subscription_status = sub.status
            current_user.subscription_id = sub.id
            db.commit()

    return {"status": current_user.subscription_status or "inactive"}


@router.get("/portal", response_model=BillingPortalOut)
def billing_portal(
    current_user: User = Depends(get_current_user),
):
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found. Please subscribe first.")

    return_url = os.getenv("STRIPE_SUCCESS_URL", "http://localhost:3001")

    portal_session = stripe.billing_portal.Session.create(
        customer=current_user.stripe_customer_id,
        return_url=return_url,
    )

    return {"url": portal_session.url}
