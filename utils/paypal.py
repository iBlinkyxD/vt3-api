import os
import uuid
import httpx

PAYPAL_CLIENT_ID     = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE          = os.getenv("PAYPAL_MODE", "sandbox")
PAYPAL_BASE = (
    "https://api-m.sandbox.paypal.com"
    if PAYPAL_MODE == "sandbox"
    else "https://api-m.paypal.com"
)


async def get_access_token() -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v1/oauth2/token",
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"PayPal auth failed: {resp.text}")
    return resp.json()["access_token"]


async def create_paypal_order(
    amount_usd: float,
    item_title: str,
    return_url: str,
    cancel_url: str,
) -> tuple[str, str]:
    """Returns (order_id, approve_url)."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v2/checkout/orders",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {"currency_code": "USD", "value": f"{amount_usd:.2f}"},
                    "description": item_title,
                }],
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "brand_name": "VT3",
                    "user_action": "PAY_NOW",
                    "landing_page": "BILLING",
                },
            },
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"PayPal order creation failed: {resp.text}")
    data = resp.json()
    approve_url = next(
        (link["href"] for link in data.get("links", []) if link["rel"] == "approve"),
        None,
    )
    return data["id"], approve_url


async def capture_paypal_order(order_id: str) -> dict:
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v2/checkout/orders/{order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"PayPal capture failed: {resp.text}")
    return resp.json()


async def send_payout(
    recipient_email: str,
    amount_usd: float,
    note: str = "VT3 fund-item payout",
) -> None:
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_BASE}/v1/payments/payouts",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "sender_batch_header": {
                    "sender_batch_id": str(uuid.uuid4()),
                    "email_subject": "You received a payment from VT3!",
                    "email_message": note,
                },
                "items": [{
                    "recipient_type": "EMAIL",
                    "amount": {"value": f"{amount_usd:.2f}", "currency": "USD"},
                    "receiver": recipient_email,
                    "note": note,
                    "sender_item_id": str(uuid.uuid4()),
                }],
            },
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"PayPal payout failed: {resp.text}")
